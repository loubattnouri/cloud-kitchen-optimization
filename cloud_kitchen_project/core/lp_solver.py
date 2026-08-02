import pulp

def solve_cloud_kitchen_lp(ingredients_supply, menu_items, max_time_minutes, ingredient_costs):
    """
    ماژول بهینه‌سازی تامین مواد اولیه و برنامه تولید منو جهت کمینه‌سازی ضایعات و بیشینه‌سازی سود
    """
    # ۱. تعریف مدل بهینه‌سازی
    model = pulp.LpProblem("Diet_Supply_Waste_Optimization", pulp.LpMaximize)

    # ۲. متغیرهای تصمیم: تعداد پرس تولیدی از هر غذا
    vars_dict = {}
    for item in menu_items:
        vars_dict[item['name']] = pulp.LpVariable(
            f"Prod_{item['name']}", 
            lowBound=item.get('min_demand', 0), 
            upBound=item.get('max_demand', None), 
            cat=pulp.LpInteger
        )

    # ۳. تابع هدف: بیشینه‌سازی سود حاصل از فروش منهای هزینه مواد اولیه مصرفی (کنترل ضایعات)
    total_revenue = pulp.lpSum([vars_dict[item['name']] * item['price'] for item in menu_items])
    
    total_material_cost = pulp.lpSum([
        vars_dict[item['name']] * item['recipe'].get(ing, 0) * ingredient_costs.get(ing, 0)
        for item in menu_items
        for ing in ingredient_costs
    ])
    
    model += (total_revenue - total_material_cost), "Net_Profit_Minus_Cost"

    # ۴. قید عدم تجاوز از موجودی انبار (انبار محدود است)
    for ingredient, max_qty in ingredients_supply.items():
        model += (
            pulp.lpSum([vars_dict[item['name']] * item['recipe'].get(ingredient, 0) for item in menu_items]) <= max_qty,
            f"Supply_Limit_{ingredient}"
        )

    # ۵. قید حداکثر زمان پخت و ظرفیت آشپزخانه
    model += (
        pulp.lpSum([vars_dict[item['name']] * item['prep_time'] for item in menu_items]) <= max_time_minutes,
        "Kitchen_Time_Limit"
    )

    # ۶. حل مسئله
    model.solve(pulp.PULP_CBC_CMD(msg=False))

    # ۷. محاسبه میزان ضایعات/باقی‌مانده مواد اولیه در انبار
    leftover_ingredients = {}
    for ingredient, max_qty in ingredients_supply.items():
        used_qty = sum(vars_dict[item['name']].varValue * item['recipe'].get(ingredient, 0) for item in menu_items)
        leftover_ingredients[ingredient] = round(max_qty - used_qty, 2)

    # ۸. خروجی نهایی جهت نمایش در داشبورد و گزارش
    results = {
        "status": pulp.LpStatus[model.status],
        "total_profit": pulp.value(model.objective),
        "production_plan": {v.name.replace("Prod_", ""): int(v.varValue) for v in model.variables()},
        "leftover_ingredients": leftover_ingredients,
        "constraints_analysis": []
    }

    # تحلیل قیود و ارزش سایه‌ای (Shadow Price)
    for name, c in model.constraints.items():
        results["constraints_analysis"].append({
            "عنوان قید": name,
            "میزان ظرفیت خالی (Slack)": c.slack,
        })

    return results