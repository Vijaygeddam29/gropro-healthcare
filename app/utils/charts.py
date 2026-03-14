def capital_allocation_chart(data, labels):
    """
    Returns chart data for capital allocation (used by templates)
    """
    total = sum(data)
    chart_data = []
    for i, label in enumerate(labels):
        pct = round((data[i] / total) * 100, 1) if total > 0 else 0
        chart_data.append({"label": label, "value": data[i], "percentage": pct})
    return chart_data
