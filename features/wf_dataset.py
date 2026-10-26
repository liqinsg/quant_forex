def walk_forward_split(df, train_months=24, valid_months=3):
    splits, start = [], df.index.min()
    while True:
        train_end = start + pd.DateOffset(months=train_months)
        valid_end = train_end + pd.DateOffset(months=valid_months)
        if valid_end > df.index.max(): break
        splits.append(((df.index>=start)&(df.index<train_end),
                       (df.index>=train_end+pd.DateOffset(days=1))&(df.index<valid_end)))
        start = valid_end
    return splits