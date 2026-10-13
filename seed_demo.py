"""
Wardrobe IQ — Demonstration Seed Script
Usage: python seed_demo.py
Creates demo user: demo_curator / password123 with full wardrobe, outfits, wears, and trip data.
"""
from datetime import date, timedelta
from app import create_app
from app.models import db, User, UserPreference, WardrobeItem, Outfit, OutfitItem, WornHistory, PointTransaction, PackingTrip, PackingItem

app = create_app()

with app.app_context():
    # Check or create demo user
    demo_user = User.query.filter_by(username="demo_curator").first()
    if not demo_user:
        demo_user = User(username="demo_curator", email="demo@wardrobeiq.local")
        demo_user.set_password("password123")
        db.session.add(demo_user)
        db.session.commit()
        print("Created demo user: demo_curator / password123")
    else:
        print("Demo user demo_curator already exists.")

    user_id = demo_user.id

    # Create/update preferences
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    if not pref:
        pref = UserPreference(
            user_id=user_id,
            preferred_styles="Minimalist, Smart Casual, Relaxed Tailoring",
            favourite_colors="Warm Ivory, Deep Forest Green, Muted Taupe, Charcoal",
            preferred_fits="Balanced / Tailored",
            common_occasions="College, Work/Office, Weekend Outings",
            comfort_preference="Balanced Style & Comfort"
        )
        db.session.add(pref)

    # Add starter capsule items if user has none
    if WardrobeItem.query.filter_by(user_id=user_id).count() == 0:
        items_data = [
            # Tops
            ("Crisp White Oxford Shirt", "Tops", "Button-down Shirt", "White", "#FFFFFF", "Solid", "Smart Casual", "All-Season", "College, Work/Office", "defaults/top_oxford_shirt.jpg", 2499.0, "Available"),
            ("Sand Linen Relaxed Tee", "Tops", "T-Shirt", "Soft Beige", "#E8DFD3", "Solid", "Casual", "Summer", "Casual, Weekend", "defaults/top_linen_tee.jpg", 1299.0, "Available"),
            ("Forest Green Merino Knit", "Tops", "Sweater", "Deep Forest Green", "#34483B", "Solid", "Minimalist", "Autumn", "College, Evening", "defaults/top_forest_sweater.jpg", 3499.0, "Worn / Needs Washing"),
            ("Charcoal Tailored Blazer", "Tops", "Blazer", "Charcoal", "#292B28", "Solid", "Formal", "All-Season", "Formal, Presentation", "defaults/top_charcoal_blazer.jpg", 7999.0, "Available"),
            
            # Bottoms
            ("Olive Tailored Chinos", "Bottoms", "Chinos", "Olive Green", "#4F6F52", "Solid", "Smart Casual", "All-Season", "College, Casual", "defaults/bottom_chinos.jpg", 2999.0, "Available"),
            ("Dark Raw Selvedge Denim", "Bottoms", "Jeans", "Navy Blue", "#1E2D4A", "Solid", "Casual", "All-Season", "Casual, Weekend", "defaults/bottom_jeans.jpg", 3999.0, "Available"),
            ("Muted Taupe Wool Trousers", "Bottoms", "Trousers", "Muted Taupe", "#8B806E", "Solid", "Formal", "Winter", "Formal, Smart Casual", "defaults/bottom_trousers.jpg", 4499.0, "In Laundry"),
            
            # Dresses
            ("Ivory Tiered Linen Dress", "Dresses / One-piece", "Shirt Dress", "Warm Ivory", "#F4EFE7", "Solid", "Minimalist", "Summer", "Brunch, Weekend", "defaults/dress_linen.jpg", 4999.0, "Available"),
            ("Sage Silk Slip Midi Dress", "Dresses / One-piece", "Slip Dress", "Sage Green", "#A9B4A1", "Solid", "Elegant", "Spring", "Dinner, Evening", "defaults/dress_slip.jpg", 5999.0, "Available"),
            
            # Footwear
            ("Minimalist White Leather Lows", "Footwear", "Sneakers", "White", "#F7F7F7", "Solid", "Casual", "All-Season", "College, Daily", "defaults/shoes_sneakers.jpg", 3999.0, "Available"),
            ("Espresso Penny Loafers", "Footwear", "Loafers", "Espresso Brown", "#3D2B1F", "Solid", "Smart Casual", "All-Season", "Formal, Office", "defaults/shoes_loafers.jpg", 5999.0, "Available"),
            ("Suede Chelsea Boots", "Footwear", "Boots", "Camel / Tan", "#9E846A", "Solid", "Smart Casual", "Autumn", "College, Evening", "defaults/shoes_boots.jpg", 6999.0, "Available"),
            
            # Accessories
            ("Vintage Minimalist Field Watch", "Accessories", "Watch", "Muted Taupe", "#C9BBA7", "Solid", "Minimalist", "All-Season", "Daily Wear", "defaults/acc_watch.jpg", 3499.0, "Available"),
            ("Woven Saddle Leather Belt", "Accessories", "Belt", "Brown", "#5C3E21", "Woven", "Smart Casual", "All-Season", "Formal, Daily", "defaults/acc_belt.jpg", 1499.0, "Available"),
            ("Canvas & Leather Weekender", "Accessories", "Bag", "Soft Beige", "#D8CBBB", "Solid", "Casual", "All-Season", "Travel, College", "defaults/acc_tote.jpg", 3999.0, "Available")
        ]

        created_items = []
        for name, cat, sub, col, hex_c, pat, sty, sea, occ, img, prc, st in items_data:
            item = WardrobeItem(
                user_id=user_id,
                name=name,
                category=cat,
                subcategory=sub,
                color=col,
                color_hex=hex_c,
                pattern=pat,
                style=sty,
                season=sea,
                occasions=occ,
                image_path=img,
                purchase_price=prc,
                availability_status=st
            )
            db.session.add(item)
            created_items.append(item)
        db.session.commit()
        print(f"Added {len(created_items)} items for demo user.")

        # Create starter outfit
        top = WardrobeItem.query.filter_by(user_id=user_id, name="Crisp White Oxford Shirt").first()
        btm = WardrobeItem.query.filter_by(user_id=user_id, name="Olive Tailored Chinos").first()
        shoe = WardrobeItem.query.filter_by(user_id=user_id, name="Minimalist White Leather Lows").first()
        watch = WardrobeItem.query.filter_by(user_id=user_id, name="Vintage Minimalist Field Watch").first()

        outfit = Outfit(
            user_id=user_id,
            title="The White & Olive Ensemble",
            occasion="College",
            style="Smart Casual",
            score=94.5,
            why_explanation="Balanced tonal contrast between White and Olive Green. Silhouette tailored for a refined Smart Casual aesthetic.",
            is_favorite=True
        )
        db.session.add(outfit)
        db.session.flush()

        db.session.add(OutfitItem(outfit_id=outfit.id, item_id=top.id, slot="top"))
        db.session.add(OutfitItem(outfit_id=outfit.id, item_id=btm.id, slot="bottom"))
        db.session.add(OutfitItem(outfit_id=outfit.id, item_id=shoe.id, slot="footwear"))
        db.session.add(OutfitItem(outfit_id=outfit.id, item_id=watch.id, slot="accessory"))
        db.session.commit()

        # Add 2 confirmed wear events
        w1 = WornHistory(
            user_id=user_id,
            outfit_id=outfit.id,
            item_ids_json=f"[{top.id}, {btm.id}, {shoe.id}, {watch.id}]",
            date_worn=date.today() - timedelta(days=2),
            notes="Worn for mid-term class presentation. Great comfort."
        )
        w2 = WornHistory(
            user_id=user_id,
            outfit_id=outfit.id,
            item_ids_json=f"[{top.id}, {btm.id}, {shoe.id}]",
            date_worn=date.today() - timedelta(days=5),
            notes="Weekend meetup with study group."
        )
        db.session.add(w1)
        db.session.add(w2)

        # Add Points transactions
        pts = [
            (50, "WELCOME_BONUS", "Welcome starting bonus to Wardrobe IQ"),
            (30, "SEED_CAPSULE", "Seeded curated capsule wardrobe collection"),
            (15, "FAVORITE_OUTFIT", "Saved 'The White & Olive Ensemble' to favourites"),
            (25, "CONFIRM_WEAR", "Confirmed wear on campus presentation"),
            (25, "CONFIRM_WEAR", "Confirmed wear on weekend study meetup")
        ]
        for p, code, desc in pts:
            db.session.add(PointTransaction(user_id=user_id, points=p, activity_type=code, description=desc))

        # Add demo travel packing trip
        trip = PackingTrip(
            user_id=user_id,
            destination="Kyoto Autumn Tour",
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=14),
            trip_purpose="Cultural Sightseeing",
            activities="Temple walking, casual dining, bullet train travel",
            luggage_limit_kg=15.0,
            laundry_access=True
        )
        db.session.add(trip)
        db.session.flush()

        # Add trip items
        trip_items = [
            (top.id, top.name, "Tops", True, 220.0),
            (btm.id, btm.name, "Bottoms", True, 450.0),
            (shoe.id, shoe.name, "Footwear", True, 750.0),
            (None, "Universal Power Adapter", "Essentials", True, 180.0),
            (None, "Minimalist Dopp Kit", "Essentials", False, 350.0)
        ]
        for wid, cname, cat, packed, wt in trip_items:
            db.session.add(PackingItem(
                trip_id=trip.id,
                wardrobe_item_id=wid,
                custom_name=cname,
                category=cat,
                is_packed=packed,
                weight_grams=wt
            ))

        db.session.commit()
        print("Demo data seeded successfully! You can log in with demo_curator / password123.")
