# train.py
import os, torch, numpy as np
from ray import tune
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

import torch
from torch_geometric.loader import DataLoader
from torch.utils.data import Dataset, Subset
from MetaNet import BioDegDataset, MetaNet          # ← import your classes

MODEL_REGISTRY = {
    "metanet":      MetaNet,
}

# ─────────────────────────────────────────────────────────────
# 1.  scale everything FIRST (no loaders yet)
# ─────────────────────────────────────────────────────────────
def scale_dataset(dataset, train_idx):
    """
    • Z-score the 4-d env vector data.u
    • Z-score BDE/BDFE (edge_attr[:, :2])
    Returns the two fitted scalers so you can save them.
    """
    ### global env u --------------------------------------------------------
    u_train   = torch.cat([dataset[i].u for i in train_idx]).numpy()
    scaler_u  = StandardScaler().fit(u_train)

    ### bond energies -------------------------------------------------------
    edge_mat  = torch.cat([dataset[i].edge_attr[:, :2]
                           for i in train_idx]).numpy()
    scaler_e  = StandardScaler().fit(edge_mat)

    ### apply to **all** rows ----------------------------------------------
    for d in dataset:
        d.u = torch.tensor(scaler_u.transform(d.u), dtype=torch.float)

        ea  = d.edge_attr
        ea_scaled = torch.tensor(scaler_e.transform(ea[:, :2]), dtype=torch.float)
        d.edge_attr = torch.cat([ea_scaled, ea[:, 2:]], dim=1)

    return scaler_u, scaler_e


# ─────────────────────────────────────────────────────────────
# 2.  split and build loaders AFTER scaling
# ─────────────────────────────────────────────────────────────
def build_loaders(dataset,
                  val_mols=2,
                  test_mols=4,
                  seed=42,
                  bs_train=32,
                  bs_eval=64):

    groups = np.array([d.compID for d in dataset])   # one label per row

    # ----- hold-out test molecules ----------------------------------------
    outer = GroupShuffleSplit(n_splits=1,
                              test_size=test_mols,
                              random_state=seed)
    train_val_idx, test_idx = next(
        outer.split(X=np.arange(len(dataset)), groups=groups))

    # ----- validation molecules from remaining pool -----------------------
    inner = GroupShuffleSplit(n_splits=1,
                              test_size=val_mols,
                              random_state=seed+1)
    train_idx, val_idx = next(
        inner.split(X=train_val_idx, groups=groups[train_val_idx]))

    # ----- NOW fit scalers on *train* rows and transform whole dataset ----
    scale_dataset(dataset, train_idx)

    # ----- wrap subsets & loaders -----------------------------------------
    train_set = Subset(dataset, train_idx)
    val_set   = Subset(dataset, val_idx)
    test_set  = Subset(dataset, test_idx)

    train_loader = DataLoader(train_set, batch_size=bs_train, shuffle=True)
    val_loader   = DataLoader(val_set,   batch_size=bs_eval,  shuffle=False)
    test_loader  = DataLoader(test_set,  batch_size=bs_eval,  shuffle=False)

    return train_loader, val_loader, test_loader


def objective(config):
    device = f"cuda:{config['gpu_id']}"
    ds     = BioDegDataset(root='biodata')   # will load processed/data.pt
    train_loader, val_loader, test_loader = build_loaders(ds)
    ModelCls = MODEL_REGISTRY[config["arch"]]
    model = ModelCls(**config["model_kwargs"]).to(device)
    
    #model = MetaNet(hidden=config["hidden"],
    #                n_layers=config["layers"]).to(device)
    opt   = torch.optim.AdamW(model.parameters(), lr=config["lr"], weight_decay=5e-4)
    lossf = torch.nn.SmoothL1Loss()

    best = -1e9
    for epoch in range(120):
        model.train()
        for batch in train_loader:
            batch = batch.to(device)
            opt.zero_grad()
            loss = lossf(model(batch), batch.y.squeeze())
            loss.backward(); opt.step()

        # ------- validation R² -------
        model.eval(); ys, preds = [], []
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(device)
                preds.append(model(batch).cpu())
                ys.append(batch.y.cpu())
        y, yhat = torch.cat(ys), torch.cat(preds)
        r2 = 1 - torch.sum((y - yhat) ** 2) / torch.sum((y - y.mean()) ** 2)

        tune.report(val_r2=r2.item())   # ← OptunaSearch / ASHA consume this
        best = max(best, r2.item())
    return best
