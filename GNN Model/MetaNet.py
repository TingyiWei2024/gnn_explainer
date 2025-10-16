import pandas as pd
import pickle

import torch
from torch_geometric.utils import from_networkx
#from torch_geometric.nn import GCNConv, global_mean_pool  # or GINConv, GATConv, etc
from torch_geometric.nn import MetaLayer, Set2Set
from torch import nn
import torch.nn.functional as F
import torch_scatter
from torch_geometric.data import InMemoryDataset

ATOM_LIST = ['C', 'O', 'N', 'H']                       # extend if needed
GLOBAL_COLS = ['temperature', 'seawater', 'concentration', 'time']

def one_hot_symbol(sym):
    vec = torch.zeros(len(ATOM_LIST))
    vec[ATOM_LIST.index(sym)] = 1.
    return vec

def nx_to_pyg(path):
    g = pickle.load(open(path, 'rb'))                  # NetworkX graph
    for n, d in g.nodes(data=True):
        d['x'] = one_hot_symbol(d['symbol'])           # torch.tensor, shape [4]

    for _, _, d in g.edges(data=True):
        bde  = d.get('bde_pred')
        bdfe = d.get('bdfe_pred')
        missing = float(bde is None or bdfe is None)   # 1 = missing
        d['edge_attr'] = torch.tensor([
            float(bde or 0.0),
            float(bdfe or 0.0),
            missing                                   # mask bit
        ], dtype=torch.float)

    data = from_networkx(g, group_node_attrs=['x'],
                            group_edge_attrs=['edge_attr'])
    return data


def row_to_sample(row, base_graph):
    sea_flag = 1.0 if row.seawater == 'sea' else 0.0   # binary
    g_vec = torch.tensor([row.temperature,
                          sea_flag,
                          row.concentration,
                          row.time], dtype=torch.float)

    data = base_graph.clone()
    data.u      = g_vec.unsqueeze(0)
    data.y      = torch.tensor([row.degradation_rate], dtype=torch.float)
    data.compID = row.component                           # optional tracking
    return data

class BioDegDataset(InMemoryDataset):
    def __init__(self, csv_path, graph_dir, transform=None, pre_transform=None):
        super().__init__('.', transform, pre_transform)
        self.df   = pd.read_csv(csv_path)

        # 4.1  cache base graphs by component
        comps = self.df['component'].unique()
        self.graph_bank = {c: nx_to_pyg(f'gpickle_graph_{i}.pkl')
                           for i, c in enumerate(comps)}

        # 4.2  build samples
        data_list = []
        for _, row in self.df.iterrows():
            base = self.graph_bank[row.component]
            data_list.append(row_to_sample(row, base))

        self.data, self.slices = self.collate(data_list)

class BioDegDatasetCached(InMemoryDataset):
    def __init__(self, path):
        super().__init__(root='.')
        self.data, self.slices = torch.load(path,weights_only=False)

class EdgeModel(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        in_dim = hidden * 4                   # src + dst + edge + u
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(), nn.Linear(hidden, hidden))

    def forward(self, src, dst, edge_attr, u, batch):
        out = torch.cat([src, dst, edge_attr, u[batch]], dim=-1)
        return self.mlp(out)

class NodeModel(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        in_dim = hidden * 3                   # x + agg(edge) + u
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(), nn.Linear(hidden, hidden))

    def forward(self, x, edge_index, edge_attr, u, batch):
        row, col = edge_index
        agg = torch_scatter.scatter_mean(edge_attr, col, dim=0,
                                         dim_size=x.size(0))
        out = torch.cat([x, agg, u[batch]], dim=-1)
        return self.mlp(out)

class GlobalModel(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        in_dim = hidden * 3                   # pooled x + pooled e + u
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(), nn.Linear(hidden, hidden))

    def forward(self, x, edge_index, edge_attr, u, batch):
        x_pool = torch_scatter.scatter_mean(x, batch, dim=0)
        row = edge_index[0]
        e_pool = torch_scatter.scatter_mean(edge_attr, batch[row], dim=0)
        out = torch.cat([u, x_pool, e_pool], dim=-1)
        return self.mlp(out)

class MetaNet(nn.Module):
    def __init__(self, hidden=64, n_layers=4):
        super().__init__()
        self.x_proj    = nn.Linear(4, hidden)
        self.edge_proj = nn.Linear(3, hidden)
        self.u_proj    = nn.Linear(4, hidden)        # NEW

        self.layers = nn.ModuleList([
            MetaLayer(EdgeModel(hidden), NodeModel(hidden), GlobalModel(hidden))
            for _ in range(n_layers)
        ])

        self.readout = Set2Set(hidden, processing_steps=3)
        self.head    = nn.Sequential(nn.LayerNorm(hidden*2),
                                     nn.Linear(hidden*2, 1))

    def forward(self, data):
        x         = F.relu(self.x_proj(data.x))
        edge_attr = F.relu(self.edge_proj(data.edge_attr))
        u         = F.relu(self.u_proj(data.u))      # shape [batch, hidden]

        for layer in self.layers:
            x, edge_attr, u = layer(x, data.edge_index,
                                    edge_attr, u, data.batch)

        g = self.readout(x, data.batch)
        return self.head(g).squeeze(-1)