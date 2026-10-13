from app.models import WardrobeItem

def generate_trip_packing_plan(user_id, days, purpose, activities, laundry_access):
    """
    Generates intelligent packing recommendations from user's available wardrobe.
    Optimizes versatility and respects laundry access.
    """
    available_items = WardrobeItem.query.filter_by(
        user_id=user_id,
        availability_status="Available"
    ).all()

    tops = [i for i in available_items if i.category == "Tops"]
    bottoms = [i for i in available_items if i.category == "Bottoms"]
    dresses = [i for i in available_items if i.category == "Dresses / One-piece"]
    shoes = [i for i in available_items if i.category == "Footwear"]
    accs = [i for i in available_items if i.category == "Accessories"]

    # Calculate item quotas based on duration and laundry access
    if laundry_access:
        target_tops = min(len(tops), max(2, (days // 2) + 1))
        target_bottoms = min(len(bottoms), 2)
    else:
        target_tops = min(len(tops), min(days, 5))
        target_bottoms = min(len(bottoms), max(2, (days // 2) + 1))

    target_shoes = min(len(shoes), 2)
    target_accs = min(len(accs), 2)

    recommended_items = []
    
    # Tops
    for t in tops[:target_tops]:
        recommended_items.append({
            "wardrobe_item_id": t.id,
            "custom_name": t.name,
            "category": "Tops",
            "weight_grams": t.weight_grams or 220.0
        })

    # Bottoms
    for b in bottoms[:target_bottoms]:
        recommended_items.append({
            "wardrobe_item_id": b.id,
            "custom_name": b.name,
            "category": "Bottoms",
            "weight_grams": b.weight_grams or 450.0
        })

    # Dresses if applicable
    if dresses and len(recommended_items) < 6:
        d = dresses[0]
        recommended_items.append({
            "wardrobe_item_id": d.id,
            "custom_name": d.name,
            "category": "Dresses / One-piece",
            "weight_grams": d.weight_grams or 350.0
        })

    # Footwear
    for s in shoes[:target_shoes]:
        recommended_items.append({
            "wardrobe_item_id": s.id,
            "custom_name": s.name,
            "category": "Footwear",
            "weight_grams": s.weight_grams or 750.0
        })

    # Accessories
    for a in accs[:target_accs]:
        recommended_items.append({
            "wardrobe_item_id": a.id,
            "custom_name": a.name,
            "category": "Accessories",
            "weight_grams": a.weight_grams or 150.0
        })

    # Essential travel staples
    recommended_items.append({
        "wardrobe_item_id": None,
        "custom_name": "Travel Tech & Chargers Organizer",
        "category": "Essentials",
        "weight_grams": 300.0
    })
    recommended_items.append({
        "wardrobe_item_id": None,
        "custom_name": "Dopp Kit / Minimalist Toiletries",
        "category": "Essentials",
        "weight_grams": 400.0
    })

    return recommended_items
