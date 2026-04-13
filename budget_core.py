#budget_core.py

def cat_total(trans):
    result = {}
    for t in trans:
        cat = t["category"]
        amt = t["amount"]
        if cat in result:
            result[cat] += amt
        else:
            result[cat] = amt
    return result

def top_cats(trans, n=3):
    result = cat_total(trans)
    sort_result = sorted(result.items(), key = lambda x: x[1],reverse = True)
    top = []
    for i in range(n):
        top.append((sort_result[i][0], sort_result[i][1]))
    return top

