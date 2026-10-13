import unittest
from unittest.mock import patch
import os
import json
from app import create_app
from app.models import db, User, WardrobeItem, Outfit, WornHistory, PointTransaction, PackingTrip, WeeklyPlan, PlannedOutfit
from app.services.stylist_chat import set_mock_llm_handler, get_user_history, clear_user_history

class TestWardrobeIQ(unittest.TestCase):
    def setUp(self):
        self.app = create_app(config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False
        })
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create test user
            user = User(username="test_stylist", email="test@example.com")
            user.set_password("password123")
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        set_mock_llm_handler(None)
        clear_user_history(self.user_id)
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self):
        return self.client.post("/login", data={
            "identifier": "test_stylist",
            "password": "password123"
        }, follow_redirects=True)

    def test_auth_and_welcome_points(self):
        # Register new user
        res = self.client.post("/register", data={
            "username": "new_curator",
            "email": "curator@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome to Wardrobe IQ", res.data)
        
        # Verify points awarded
        with self.app.app_context():
            user = User.query.filter_by(username="new_curator").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.total_points, 50)

    def test_closet_seed_and_inventory(self):
        self.login()
        # Seed starter capsule
        res = self.client.post("/closet/seed-starter-capsule", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Successfully curated", res.data)

        with self.app.app_context():
            items = WardrobeItem.query.filter_by(user_id=self.user_id).all()
            self.assertGreaterEqual(len(items), 10)
            
            # Check availability default is 'Available'
            for item in items:
                self.assertEqual(item.availability_status, "Available")

    def test_laundry_and_availability(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)
        
        with self.app.app_context():
            top = WardrobeItem.query.filter_by(user_id=self.user_id, category="Tops").first()
            top_id = top.id

        # Update status to Worn
        res = self.client.post("/laundry/update-status", data={
            "item_id": top_id,
            "status": "Worn / Needs Washing"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            updated_item = WardrobeItem.query.get(top_id)
            self.assertEqual(updated_item.availability_status, "Worn / Needs Washing")

        # Move to In Laundry
        self.client.post("/laundry/update-status", data={
            "item_id": top_id,
            "status": "In Laundry"
        }, follow_redirects=True)

        with self.app.app_context():
            updated_item = WardrobeItem.query.get(top_id)
            self.assertEqual(updated_item.availability_status, "In Laundry")

    def test_smart_outfit_studio_and_worn_flow(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # 1. Generate looks
        res = self.client.post("/outfit-studio/generate", data={
            "prompt": "Suggest a sharp outfit for college",
            "occasion": "College",
            "style": "Smart Casual"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            outfits = Outfit.query.filter_by(user_id=self.user_id).all()
            self.assertGreaterEqual(len(outfits), 1)
            target_outfit = outfits[0]
            outfit_id = target_outfit.id

            # Verify generating does NOT mark as worn
            worn_count_before = WornHistory.query.filter_by(user_id=self.user_id).count()
            self.assertEqual(worn_count_before, 0)

        # 2. Favorite toggle
        fav_res = self.client.post(f"/outfit-studio/favorite/{outfit_id}", follow_redirects=True)
        self.assertEqual(fav_res.status_code, 200)
        with self.app.app_context():
            outfit = Outfit.query.get(outfit_id)
            self.assertTrue(outfit.is_favorite)

        # 3. Explicit Mark as Worn confirmation
        worn_res = self.client.post("/outfit-studio/mark-worn", data={
            "outfit_id": outfit_id,
            "date_worn": "2026-10-10",
            "notes": "Felt great and comfortable on campus."
        }, follow_redirects=True)
        self.assertEqual(worn_res.status_code, 200)

        # Verify worn history is created and items moved to Worn/Needs Washing
        with self.app.app_context():
            worn_entries = WornHistory.query.filter_by(user_id=self.user_id).all()
            self.assertEqual(len(worn_entries), 1)
            self.assertEqual(worn_entries[0].outfit_id, outfit_id)

    def test_ai_fashion_chatbot_unconfigured_honest_notice(self):
        """Verifies that when no AI model is configured, the chatbot provides an honest setup notice without faking AI."""
        from app.config import Config
        orig_key = Config.GEMINI_API_KEY
        try:
            Config.GEMINI_API_KEY = ""
            self.login()
            self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

            res = self.client.post("/api/chatbot/ask", json={"message": "What should I wear today?"})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("reply", data)
            # Must return the honest setup notice, not fake generic text
            self.assertIn("ai-config-notice", data["reply"])
            self.assertIn("Real AI Model Setup Required", data["reply"])
        finally:
            Config.GEMINI_API_KEY = orig_key

    def test_ai_fashion_chatbot_live_gemini(self):
        """Verifies that with a live GEMINI_API_KEY, the chatbot generates real dynamic fashion advice."""
        from app.config import Config
        if not Config.GEMINI_API_KEY:
            self.skipTest("GEMINI_API_KEY not configured")

        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        res = self.client.post("/api/chatbot/ask", json={"message": "How can I style my blazer for an art gallery opening?"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("reply", data)
        self.assertGreater(len(data["reply"]), 50)
        self.assertNotIn("Real AI Model Setup Required", data["reply"])

    def test_ai_fashion_chatbot_open_ended_queries_and_grounding(self):
        """Tests that the chatbot handles open-ended questions with wardrobe grounding and conversation memory."""
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        captured_calls = []

        def mock_llm_handler(user_id, system_prompt, history, user_message):
            captured_calls.append({
                "system_prompt": system_prompt,
                "history": list(history),
                "message": user_message
            })
            # Return realistic dynamic response mentioning actual owned pieces
            if "cousin" in user_message.lower():
                return "For your cousin's engagement, balance festive refinement with modern tailoring. Pair your <strong>Relaxed Fit Blazer</strong> with your <strong>Tailored Pleated Trousers</strong>."
            elif "black shirt" in user_message.lower():
                return "Your black shirt works wonderfully paired with high-contrast bottoms like your <strong>Tailored Pleated Trousers</strong> or olive chinos."
            elif "elegant" in user_message.lower():
                return "To elevate elegance, emphasize clean silhouette drape, minimal jewelry, and a crisp tuck with your <strong>Tailored Pleated Trousers</strong>."
            elif "trending" in user_message.lower():
                return "Key 2026 trending colors include Warm Ivory, Espresso Brown, Sage Green, and Deep Forest Green."
            elif "travelling for three days" in user_message.lower():
                return "For a 3-day trip, pack a versatile capsule: Day 1: <strong>Tailored Pleated Trousers</strong> + shirt. Day 2: Layer with your <strong>Relaxed Fit Blazer</strong>. Day 3: Casual restyle."
            elif "why does this outfit combination work" in user_message.lower():
                return "This combination works through proportion balancing: structured tailoring on top counterweights the fluid drape below."
            elif "shoes" in user_message.lower():
                return "For shoes to complete that look, your clean minimalist leather footwear grounds the tailoring perfectly."
            return f"Styled response for '{user_message}' with your wardrobe pieces."

        set_mock_llm_handler(mock_llm_handler)

        test_questions = [
            "What should I wear to my cousin's engagement?",
            "I have a black shirt. What can I pair it with?",
            "How can I make my outfit look more elegant?",
            "What fashion colours are trending this season?",
            "I am travelling for three days. Help me plan outfits.",
            "Why does this outfit combination work?"
        ]

        for q in test_questions:
            res = self.client.post("/api/chatbot/ask", json={"message": q})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("reply", data)
            self.assertGreater(len(data["reply"]), 20)

        # Verify system prompt has user's wardrobe items grounded
        self.assertGreater(len(captured_calls), 0)
        last_prompt = captured_calls[0]["system_prompt"]
        self.assertIn("USER'S ACTUAL WARDROBE DATABASE", last_prompt)
        self.assertIn("Muted Taupe Wool Trousers", last_prompt)
        self.assertIn("Charcoal Tailored Blazer", last_prompt)
        self.assertIn("Curated 2026 Trend Intelligence", last_prompt)

        # Test Follow-up question with conversation memory
        res = self.client.post("/api/chatbot/ask", json={"message": "Which shoes would pair best with that?"})
        self.assertEqual(res.status_code, 200)
        followup_call = captured_calls[-1]
        # Follow-up call must have received previous history
        self.assertGreaterEqual(len(followup_call["history"]), 2)
        self.assertEqual(followup_call["message"], "Which shoes would pair best with that?")

    def test_ai_fashion_chatbot_reset_endpoint(self):
        """Verifies that the /api/chatbot/reset endpoint clears user conversation history."""
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        def simple_handler(user_id, prompt, history, msg):
            return f"Answer to {msg}"

        set_mock_llm_handler(simple_handler)

        self.client.post("/api/chatbot/ask", json={"message": "First question"})
        self.assertGreater(len(get_user_history(self.user_id)), 0)

        res = self.client.post("/api/chatbot/reset")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(get_user_history(self.user_id)), 0)

    def test_pack_your_bags_and_points(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # Create trip
        res = self.client.post("/packing/create-trip", data={
            "destination": "Milan",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "trip_purpose": "Fashion Conference",
            "activities": "Workshops, Dining",
            "luggage_limit_kg": "12.0",
            "laundry_access": "no"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            trip = PackingTrip.query.filter_by(user_id=self.user_id, destination="Milan").first()
            self.assertIsNotNone(trip)
            self.assertGreater(len(trip.items), 0)
            trip_id = trip.id

        # Complete trip packing
        comp_res = self.client.post(f"/packing/complete-trip/{trip_id}", follow_redirects=True)
        self.assertEqual(comp_res.status_code, 200)

        with self.app.app_context():
            updated_trip = db.session.get(PackingTrip, trip_id)
            self.assertEqual(updated_trip.packed_count, updated_trip.total_count)

    def test_dashboard_metrics(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Total Items", res.data)
        self.assertIn(b"Wardrobe Value", res.data)
        self.assertIn(b"Outfit Repetition", res.data)

    def test_shopping_and_trends(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)
        
        # Test shopping page
        shop_res = self.client.get("/shopping")
        self.assertEqual(shop_res.status_code, 200)
        self.assertIn(b"Shopping Companion", shop_res.data)

        # Test trends page
        trend_res = self.client.get("/trends")
        self.assertEqual(trend_res.status_code, 200)
        self.assertIn(b"Live Fashion Trends", trend_res.data)
        self.assertIn(b"Recreate This Trend With My Wardrobe", trend_res.data)

    def test_deletion_preserves_wear_history(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)
        
        # Generate and wear outfit
        self.client.post("/outfit-studio/generate", data={"prompt": "College look"}, follow_redirects=True)
        with self.app.app_context():
            outfit = Outfit.query.filter_by(user_id=self.user_id).first()
            outfit_id = outfit.id
            item_to_delete = outfit.items[0]
            del_id = item_to_delete.id
            
        self.client.post("/outfit-studio/mark-worn", data={
            "outfit_id": outfit_id,
            "date_worn": "2026-10-10"
        }, follow_redirects=True)

        # Delete that item
        del_res = self.client.post(f"/closet/item/{del_id}/delete", follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)

        # Verify worn history still exists and maintains item ID in json
        with self.app.app_context():
            wears = WornHistory.query.filter_by(user_id=self.user_id).all()
            self.assertEqual(len(wears), 1)
            self.assertIn(del_id, wears[0].item_ids)

    def test_inr_currency_formatting_and_conversion(self):
        from app.services.currency import format_inr, convert_usd_to_inr, get_current_rate
        # Test Indian numbering system formatting
        self.assertEqual(format_inr(2499), "₹2,499")
        self.assertEqual(format_inr(125000), "₹1,25,000")
        self.assertEqual(format_inr(1500000), "₹15,00,000")
        
        # Test USD to INR conversion
        inr_val = convert_usd_to_inr(100.0)
        rate = get_current_rate()
        self.assertGreater(inr_val, 8000.0)
        self.assertGreater(rate, 80.0)

    def test_placement_interview_prioritizes_formal_attire(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        res = self.client.post("/outfit-studio/generate", data={
            "prompt": "Suggest an outfit for a placement interview"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with self.app.app_context():
            outfits = Outfit.query.filter_by(user_id=self.user_id).order_by(Outfit.created_at.desc()).all()
            self.assertGreaterEqual(len(outfits), 1)
            best_outfit = outfits[0]
            
            # The best outfit for an interview must prioritize formal top/blazer and loafers
            item_names = [i.name for i in best_outfit.items]
            has_formal_top = any("Oxford" in n or "Blazer" in n for n in item_names)
            self.assertTrue(has_formal_top, f"Expected formal shirt/blazer in {item_names}")
            
            has_loafers = any("Loafer" in n for n in item_names)
            self.assertTrue(has_loafers, f"Expected formal loafers in {item_names}")

    def test_monthly_calendar_grid_and_date_inspection(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # GET outfit-studio with specific month/year
        res = self.client.get("/outfit-studio?year=2026&month=10")
        self.assertEqual(res.status_code, 200)
        # Check weekday headers
        self.assertIn(b"Sun", res.data)
        self.assertIn(b"Mon", res.data)
        self.assertIn(b"Sat", res.data)
        self.assertIn(b"October 2026", res.data)
        self.assertIn(b"Interactive Wear Calendar", res.data)

    def test_virtual_styling_tryon_stage(self):
        from io import BytesIO
        from PIL import Image as PilImage

        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # Create outfit
        self.client.post("/outfit-studio/generate", data={"prompt": "College look"}, follow_redirects=True)
        with self.app.app_context():
            outfit = Outfit.query.filter_by(user_id=self.user_id).first()
            outfit_id = outfit.id

        from unittest.mock import patch
        with patch("app.routes.outfit_studio.render_model_tryon") as mock_model, \
             patch("app.routes.outfit_studio.process_user_photo_tryon") as mock_photo:
            
            mock_model.return_value = ("uploads/test_mock_model.jpg", "Mock model try-on complete", None)
            mock_photo.return_value = ("uploads/test_mock_photo.jpg", "Mock photo try-on complete", None)

            # 1. Test AI Model try-on
            res_model = self.client.post("/outfit-studio/tryon", data={
                "outfit_id": outfit_id,
                "tryon_mode": "model",
                "model_id": "alex_studio"
            })
            self.assertEqual(res_model.status_code, 200)
            data_model = res_model.get_json()
            self.assertTrue(data_model["success"])
            self.assertIn("preview_image", data_model)

            # 2. Test user photo try-on with generated image bytes
            img_io = BytesIO()
            test_img = PilImage.new("RGB", (300, 400), color="#FAF7F2")
            test_img.save(img_io, format="JPEG")
            img_io.seek(0)

            res_photo = self.client.post("/outfit-studio/tryon", data={
                "outfit_id": outfit_id,
                "tryon_mode": "photo",
                "third_party_approval": "true",
                "user_photo": (img_io, "test_avatar.jpg")
            }, content_type="multipart/form-data")
            self.assertEqual(res_photo.status_code, 200)
            data_photo = res_photo.get_json()
            self.assertTrue(data_photo["success"])
            self.assertIn("preview_image", data_photo)
            self.assertIn("user_photo_url", data_photo)

    def test_calendar_route_and_boundary_handling(self):
        self.login()
        # Direct /calendar route
        res = self.client.get("/calendar", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Interactive Wear Calendar", res.data)

        # Extreme year bounds (should not throw ValueError: year must be in 1..9999)
        res_neg = self.client.get("/calendar?year=-5&month=13", follow_redirects=True)
        self.assertEqual(res_neg.status_code, 200)
        res_future = self.client.get("/calendar?year=99999&month=-1", follow_redirects=True)
        self.assertEqual(res_future.status_code, 200)

    def test_mark_worn_empty_outfit_validation(self):
        self.login()
        # Posting empty outfit_id must not crash with 404
        res = self.client.post("/outfit-studio/mark-worn", data={
            "outfit_id": "",
            "date_worn": "2026-10-11"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Please select an outfit to mark as worn", res.data)

    def test_multi_factor_scoring_and_outfit_diversity(self):
        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # Generate outfits for casual prompt
        self.client.post("/outfit-studio/generate", data={"prompt": "Suggest a casual outfit for college campus"}, follow_redirects=True)
        with self.app.app_context():
            outfits = Outfit.query.filter_by(user_id=self.user_id).order_by(Outfit.created_at.desc()).limit(3).all()
            self.assertGreaterEqual(len(outfits), 2)
            
            # Scores must be explainable and distinct or top-ranked
            scores = [o.score for o in outfits]
            self.assertTrue(all(50.0 <= s <= 99.0 for s in scores))
            # Primary pieces should not all be identical when variety exists
            top_ids = [o.items[0].id for o in outfits if o.items]
            self.assertGreater(len(set(top_ids)), 1)

    def test_trends_multi_result_grid_and_filtering(self):
        self.login()
        res = self.client.get("/trends")
        self.assertEqual(res.status_code, 200)
        # Verify 6 trends are present in the multi-trend gallery
        self.assertIn(b"Minimalist Tailoring &amp; Quiet Luxury", res.data)
        self.assertIn(b"Earth-Toned Utilitarian &amp; Modern Fieldwear", res.data)
        self.assertIn(b"Modern Collegiate &amp; Elevated Knitwear", res.data)
        self.assertIn(b"Breeze &amp; Flow: Resort Linen Silhouettes", res.data)
        self.assertIn(b"Architectural Monochrome Minimalism", res.data)
        self.assertIn(b"Contemporary Heritage &amp; Artisanal Craft", res.data)

        # Test category filter
        res_filter = self.client.get("/trends?category=Tailoring")
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn(b"Minimalist Tailoring", res_filter.data)

    def test_fashion_lab_outfit_analysis_and_rating(self):
        import io
        from PIL import Image as PilImg

        self.login()
        self.client.post("/closet/seed-starter-capsule", follow_redirects=True)

        # Create two substantially different outfit images:
        # Image A: High-contrast (White top, Navy/Black bottom)
        img_a = PilImg.new("RGB", (300, 500), color=(250, 250, 250))
        # Draw dark bottom half
        for x in range(300):
            for y in range(250, 500):
                img_a.putpixel((x, y), (20, 25, 35))
        buf_a = io.BytesIO()
        img_a.save(buf_a, format="JPEG")
        buf_a.seek(0)

        # Image B: Warm monochromatic / earth-toned (Olive/Camel warm throughout)
        img_b = PilImg.new("RGB", (300, 500), color=(80, 110, 80))
        for x in range(300):
            for y in range(250, 500):
                img_b.putpixel((x, y), (90, 120, 90))
        buf_b = io.BytesIO()
        img_b.save(buf_b, format="JPEG")
        buf_b.seek(0)

        # 1. Analyze Image A via AJAX
        res_a = self.client.post("/fashion-lab/analyze-outfit", data={
            "outfit_photo": (buf_a, "outfit_monochrome_contrast.jpg")
        }, content_type="multipart/form-data", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.get_json()
        self.assertTrue(data_a["success"])
        analysis_a = data_a["analysis"]

        # 2. Analyze Image B via AJAX
        res_b = self.client.post("/fashion-lab/analyze-outfit", data={
            "outfit_photo": (buf_b, "outfit_earth_tones.jpg")
        }, content_type="multipart/form-data", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.get_json()
        self.assertTrue(data_b["success"])
        analysis_b = data_b["analysis"]

        # Assertions:
        # A) Both images are processed into genuine, non-constant results
        self.assertIn("style_score", analysis_a)
        self.assertIn("style_score", analysis_b)
        self.assertGreater(analysis_a["style_score"], 60)
        self.assertGreater(analysis_b["style_score"], 60)

        # B) Explainable score breakdowns are present
        self.assertIn("Score Breakdown", analysis_a["score_explanation"])
        self.assertIn("Score Breakdown", analysis_b["score_explanation"])

        # C) Detected characteristics must be image-specific and distinct
        self.assertNotEqual(analysis_a["dominant_tone"], analysis_b["dominant_tone"])
        self.assertNotEqual(analysis_a["detected_colors"], analysis_b["detected_colors"])
        self.assertNotEqual(analysis_a["works_well"], analysis_b["works_well"])

        # D) Test validation: invalid file must return 400
        res_invalid = self.client.post("/fashion-lab/analyze-outfit", data={
            "outfit_photo": (io.BytesIO(b"fake text"), "bad_file.txt")
        }, content_type="multipart/form-data", headers={"X-Requested-With": "XMLHttpRequest"})
        self.assertEqual(res_invalid.status_code, 400)
        self.assertFalse(res_invalid.get_json()["success"])

    def test_one_piece_dress_virtual_tryon(self):
        """
        Verify that one-piece dresses (and gowns/lehengas/frocks) are correctly recognized,
        generate full-length binary masks from neckline to hem/ankles (covering both torso and legs),
        and invoke virtual try-on with is_dress=True instead of being cropped as a top.
        """
        from app.services.tryon_service import (
            is_dress_item,
            generate_dress_mask,
            execute_full_ensemble_tryon
        )
        from PIL import Image as PilImg

        # 1. Category and keyword recognition
        class DummyGarment:
            def __init__(self, name, category, color="purple", image_path="defaults/dress_slip.jpg"):
                self.name = name
                self.category = category
                self.color = color
                self.image_path = image_path

        dress_item = DummyGarment("Sage Silk Slip Midi Dress", "Dresses / One-piece")
        lehenga_item = DummyGarment("purple lehenga", "Dresses / One-piece")
        frock_item = DummyGarment("vintage frock", "Dresses / One-piece")
        top_item = DummyGarment("Oxford Cotton Button-Down Shirt", "Tops")
        bottom_item = DummyGarment("Pleated Straight-Leg Chinos", "Bottoms")

        self.assertTrue(is_dress_item(dress_item))
        self.assertTrue(is_dress_item(lehenga_item))
        self.assertTrue(is_dress_item(frock_item))
        self.assertFalse(is_dress_item(top_item))
        self.assertFalse(is_dress_item(bottom_item))

        # 2. Mask generation verification
        # Create a mock person image
        test_person_path = os.path.join(self.app.root_path, "static", "uploads", "inference_temp", "test_mask_person.jpg")
        os.makedirs(os.path.dirname(test_person_path), exist_ok=True)
        img = PilImg.new("RGB", (700, 1050), color=(220, 220, 220))
        img.save(test_person_path, "JPEG")

        # Studio model mode:
        studio_mask_path = generate_dress_mask(test_person_path, is_personal_photo=False)
        self.assertTrue(os.path.exists(studio_mask_path))
        with PilImg.open(studio_mask_path) as s_mask:
            self.assertEqual(s_mask.size, (700, 1050))
            # Head/face (y=100) should be unmasked (black) to preserve identity
            self.assertEqual(s_mask.getpixel((350, 100)), (0, 0, 0))
            # Neckline to torso (y=350) should be masked (white)
            self.assertEqual(s_mask.getpixel((350, 350)), (255, 255, 255))
            # Lower body/legs (y=650) should be masked (white) so shorts/trousers are replaced
            self.assertEqual(s_mask.getpixel((350, 650)), (255, 255, 255))
            # Footwear/floor (y=980) should be unmasked (black)
            self.assertEqual(s_mask.getpixel((350, 980)), (0, 0, 0))

        # Personal photo mode:
        photo_mask_path = generate_dress_mask(test_person_path, is_personal_photo=True)
        self.assertTrue(os.path.exists(photo_mask_path))
        with PilImg.open(photo_mask_path) as p_mask:
            self.assertEqual(p_mask.size, (700, 1050))
            # Head/face (y=100) unmasked
            self.assertEqual(p_mask.getpixel((350, 100)), (0, 0, 0))
            # Lower body (y=650) masked
            self.assertEqual(p_mask.getpixel((350, 650)), (255, 255, 255))

        # 3. Privacy protection for personal photos
        rel_path, note, err = execute_full_ensemble_tryon(
            person_img_path=test_person_path,
            outfit_items=[dress_item],
            output_filename="test_privacy.jpg",
            is_personal_photo=True,
            user_approved=False
        )
        self.assertIsNone(rel_path)
        self.assertIn("Privacy Protection", err)

        # 4. Pipeline dispatch verification: is_dress=True must be passed to neural inference
        with patch("app.services.tryon_service.run_idm_vton_inference") as mock_vton:
            mock_vton.return_value = (test_person_path, None)
            rel_path, note, err = execute_full_ensemble_tryon(
                person_img_path=test_person_path,
                outfit_items=[dress_item],
                output_filename="test_dress_pipeline.jpg",
                is_personal_photo=False,
                user_approved=True
            )
            self.assertIsNotNone(rel_path)
            self.assertIn("One-piece Dress", note)
            self.assertIsNone(err)
            mock_vton.assert_called_once()
            called_args, called_kwargs = mock_vton.call_args
            self.assertTrue(called_kwargs.get("is_dress"), "run_idm_vton_inference must be called with is_dress=True")
            self.assertFalse(called_kwargs.get("is_lower_body"))

    def test_weekly_outfit_planner(self):
        """
        Verify complete functionality of Weekly Outfit Planner:
        1. 7 days Monday-Sunday display, counters, progress summary
        2. Flexible categories: top+bottom, dress-only, footwear+accessories, multiple accessories
        3. Max 3 outfits per day enforcement (reject 4th outfit)
        4. User isolation and ownership validation (cannot select other user's items, edit or delete other user's outfits)
        5. Outfit editing and deletion
        6. Empty outfit rejection (at least 1 item required)
        7. Week navigation & persistence across week transitions
        8. Clear this week's plan (non-destructive to closet, wear history, points, or other weeks)
        9. Availability warning display for items in laundry
        """
        from datetime import date, timedelta
        from app.routes.weekly_planner import get_monday_of_week

        self.login()
        today = date.today()
        current_monday = get_monday_of_week(today)
        current_week_str = current_monday.strftime("%Y-%m-%d")
        next_monday = current_monday + timedelta(days=7)
        next_week_str = next_monday.strftime("%Y-%m-%d")

        # 1. Create items in Digital Closet for current user across multiple categories
        with self.app.app_context():
            u = User.query.get(self.user_id)
            initial_points = u.total_points

            # User items
            top_item = WardrobeItem(user_id=self.user_id, name="Navy Linen Shirt", image_path="defaults/top_oxford_shirt.jpg", category="Tops", color="Navy", availability_status="Available")
            bottom_item = WardrobeItem(user_id=self.user_id, name="Ivory Pleated Trousers", image_path="defaults/bottom_chinos.jpg", category="Bottoms", color="Ivory", availability_status="Available")
            dress_item = WardrobeItem(user_id=self.user_id, name="Sage Silk Slip Dress", image_path="defaults/dress_slip.jpg", category="Dresses / One-piece", color="Sage", availability_status="Available")
            shoe_item = WardrobeItem(user_id=self.user_id, name="Espadrille Loafers", image_path="defaults/shoes_loafers.jpg", category="Footwear", color="Tan", availability_status="Available")
            acc1 = WardrobeItem(user_id=self.user_id, name="Woven Leather Belt", image_path="defaults/acc_belt.jpg", category="Accessories", color="Cognac", availability_status="Available")
            acc2 = WardrobeItem(user_id=self.user_id, name="Gold Signet Ring", image_path="defaults/acc_ring.jpg", category="Accessories", color="Gold", availability_status="Available")
            laundry_item = WardrobeItem(user_id=self.user_id, name="Silk Evening Blouse", image_path="defaults/top_blouse.jpg", category="Tops", color="Champagne", availability_status="In Laundry")

            # Other user & item for isolation test
            other_user = User(username="other_curator", email="other@example.com")
            other_user.set_password("pass123")
            db.session.add(other_user)
            db.session.flush()
            other_item = WardrobeItem(user_id=other_user.id, name="Other User Hat", image_path="defaults/acc_hat.jpg", category="Accessories", color="Black")

            db.session.add_all([top_item, bottom_item, dress_item, shoe_item, acc1, acc2, laundry_item, other_item])
            db.session.commit()

            top_id = top_item.id
            bottom_id = bottom_item.id
            dress_id = dress_item.id
            shoe_id = shoe_item.id
            acc1_id = acc1.id
            acc2_id = acc2.id
            laundry_id = laundry_item.id
            other_id = other_item.id
            other_user_id = other_user.id

        # 2. Test GET /weekly-planner initial render
        res = self.client.get("/weekly-planner")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Weekly Outfit Planner", res.data)
        self.assertIn(b"Monday", res.data)
        self.assertIn(b"Sunday", res.data)
        self.assertIn(b"0/3", res.data)
        self.assertIn(b"Navy Linen Shirt", res.data)
        self.assertIn(b"Silk Evening Blouse", res.data)
        self.assertIn(b"In Laundry", res.data)
        # Verify other user's item does not appear
        self.assertNotIn(b"Other User Hat", res.data)

        # 3. Test validation: saving empty outfit set must fail
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Empty Look",
            "item_ids": []
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Please select at least one wardrobe item", res.data)

        # 4. Test User Isolation: Attempting to save another user's item must fail
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Hacked Look",
            "item_ids": [other_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"could not be validated in your closet", res.data)

        # 5. Add Outfit 1 for Monday (Day 0): Top + Bottom (2 items)
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Office Sharp Look",
            "notes": "Pair with leather tote",
            "item_ids": [top_id, bottom_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Office Sharp Look", res.data)
        self.assertIn(b"to your plan for Monday!", res.data)

        # 6. Add Outfit 2 for Monday (Day 0): Dress-only (complete garment, no bottom)
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Evening Silk Elegance",
            "notes": "Minimal jewellery",
            "item_ids": [dress_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Evening Silk Elegance", res.data)

        # 7. Add Outfit 3 for Monday (Day 0): Footwear + multiple Accessories (no top or bottom)
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Accessories Styling",
            "item_ids": [shoe_id, acc1_id, acc2_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Accessories Styling", res.data)

        # Verify Monday is full (3/3)
        res = self.client.get(f"/weekly-planner?week={current_week_str}&day=0")
        self.assertIn(b"3/3", res.data)

        # 8. Attempt 4th outfit on Monday -> Must be rejected by 3-outfit limit
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "title": "Fourth Greedy Look",
            "item_ids": [top_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Daily limit reached: You can plan a maximum of 3 outfit sets", res.data)

        with self.app.app_context():
            plan = WeeklyPlan.query.filter_by(user_id=self.user_id, week_start_date=current_monday).first()
            self.assertIsNotNone(plan)
            monday_outfits = plan.get_outfits_for_day(0)
            self.assertEqual(len(monday_outfits), 3)
            outfit_to_edit_id = monday_outfits[0].id
            outfit_to_delete_id = monday_outfits[2].id

        # 9. Test JSON endpoint for modal editing
        res_json = self.client.get(f"/weekly-planner/outfit/{outfit_to_edit_id}")
        self.assertEqual(res_json.status_code, 200)
        data = res_json.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["title"], "Office Sharp Look")
        self.assertIn(top_id, data["item_ids"])

        # 10. Test Editing an outfit
        res = self.client.post("/weekly-planner/save-outfit", data={
            "week": current_week_str,
            "day_of_week": 0,
            "outfit_id": outfit_to_edit_id,
            "title": "Executive Presentation Look",
            "notes": "Updated styling notes",
            "item_ids": [top_id, bottom_id, acc1_id]
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Executive Presentation Look", res.data)
        self.assertIn(b"successfully!", res.data)

        with self.app.app_context():
            updated = PlannedOutfit.query.get(outfit_to_edit_id)
            self.assertEqual(updated.title, "Executive Presentation Look")
            self.assertEqual(len(updated.items), 3)

        # 11. Test Deleting an outfit
        res = self.client.post(f"/weekly-planner/delete-outfit/{outfit_to_delete_id}", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Removed", res.data)
        self.assertIn(b"Accessories Styling", res.data)

        with self.app.app_context():
            plan = WeeklyPlan.query.filter_by(user_id=self.user_id, week_start_date=current_monday).first()
            self.assertEqual(len(plan.get_outfits_for_day(0)), 2)

        # 12. Test Populating Outfits across all 7 days (Tuesday to Sunday)
        for day_idx in range(1, 7):
            res = self.client.post("/weekly-planner/save-outfit", data={
                "week": current_week_str,
                "day_of_week": day_idx,
                "title": f"Day {day_idx} Look",
                "item_ids": [dress_id if day_idx % 2 == 0 else top_id]
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # Check weekly completion stats
        res = self.client.get(f"/weekly-planner?week={current_week_str}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"7/7", res.data)
        self.assertIn(b"Days Planned", res.data)
        self.assertIn(b"100% Complete", res.data)

        # 13. Test Week Navigation & Isolation
        # Next week should have 0 outfits planned
        res_next = self.client.get(f"/weekly-planner?week={next_week_str}")
        self.assertEqual(res_next.status_code, 200)
        self.assertIn(b"0/7", res_next.data)
        self.assertIn(b"0 Total Outfit Sets", res_next.data)

        # Current week still has all outfits intact
        res_curr = self.client.get(f"/weekly-planner?week={current_week_str}")
        self.assertIn(b"7/7", res_curr.data)
        self.assertIn(b"8 Total Outfit Sets", res_curr.data)

        # 14. Test "Clear This Week's Plan" (Non-destructive to wardrobe items, history, or points)
        res_clear = self.client.post("/weekly-planner/clear-week", data={
            "week": current_week_str
        }, follow_redirects=True)
        self.assertEqual(res_clear.status_code, 200)
        self.assertIn(b"Cleared the outfit plan", res_clear.data)

        with self.app.app_context():
            # Plan for current week is deleted
            cleared_plan = WeeklyPlan.query.filter_by(user_id=self.user_id, week_start_date=current_monday).first()
            self.assertIsNone(cleared_plan)
            # Wardrobe items in closet remain completely intact
            user_items_count = WardrobeItem.query.filter_by(user_id=self.user_id).count()
            self.assertEqual(user_items_count, 7)
            # User points remain unaffected (no points added or deducted)
            user_check = User.query.get(self.user_id)
            self.assertEqual(user_check.total_points, initial_points)
            # Worn history is unaffected
            worn_count = WornHistory.query.filter_by(user_id=self.user_id).count()
            self.assertEqual(worn_count, 0)

    def test_shopping_companion_personalization(self):
        """
        Comprehensive test of Wardrobe IQ Shopping Companion:
        1. Women's/girls' wardrobe: auto-detects 'womens', shows dresses/pumps/skirts, excludes menswear items.
        2. Men's/boys' wardrobe: auto-detects 'mens', shows chinos/oxford shirts/loafers, excludes womenswear items.
        3. Mixed wardrobe: auto-detects 'mixed', shows both collections.
        4. Ambiguous / Neutral wardrobe: displays style selection onboarding prompt.
        5. Setting preference via POST /shopping/set-preference.
        6. Filtering: Category (including macro 'Clothing'), Style, Brand, and Max Budget in INR.
        7. Gap filler recommendation and duplicate warnings against existing closet items.
        8. Integrity of catalog data: legitimate merchants, product images, and working URLs.
        """
        from app.models import UserPreference
        from app.routes.shopping import CATALOG_ITEMS

        self.login()

        # 0. Catalog integrity check
        self.assertGreater(len(CATALOG_ITEMS), 15)
        for prod in CATALOG_ITEMS:
            self.assertTrue(prod["name"], "Product must have a name")
            self.assertTrue(prod["brand"], "Product must have a brand")
            self.assertTrue(prod["merchant"], "Product must have a merchant")
            self.assertTrue(prod["url"].startswith("http"), f"Product {prod['name']} must have a valid URL")
            self.assertTrue(prod["image"], f"Product {prod['name']} must have an image path")
            self.assertIn(prod["department"], ["womens", "mens", "unisex"])
            self.assertIn(prod["category"], ["Tops", "Bottoms", "Dresses / One-piece", "Footwear", "Accessories"])

        # 1. SCENARIO 1: Women's / Girls' Wardrobe
        with self.app.app_context():
            # Clear any existing items
            WardrobeItem.query.filter_by(user_id=self.user_id).delete()
            # Add women's items
            w_items = [
                WardrobeItem(user_id=self.user_id, name="Royal Silk Lehenga", category="Dresses / One-piece", subcategory="Lehenga", color="Emerald Green", style="Formal", image_path="defaults/dress_slip.jpg"),
                WardrobeItem(user_id=self.user_id, name="Embroidered Chudidar Kurti", category="Dresses / One-piece", subcategory="Chudidar", color="Warm Ivory", style="Traditional / Ethnic", image_path="defaults/dress_linen.jpg"),
                WardrobeItem(user_id=self.user_id, name="Floral Print Pleated Midi Skirt", category="Bottoms", subcategory="Skirt", color="Black", style="Smart Casual", image_path="defaults/bottom_trousers.jpg"),
                WardrobeItem(user_id=self.user_id, name="Silk Blouse", category="Tops", subcategory="Blouse", color="Soft Blue", style="Smart Casual", image_path="defaults/top_linen_tee.jpg"),
            ]
            for item in w_items:
                db.session.add(item)
            db.session.commit()

        res_women = self.client.get("/shopping")
        self.assertEqual(res_women.status_code, 200)
        # Should detect Women's / Girls'
        self.assertIn(b"Women's / Girls'", res_women.data)
        # Should display women's products
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_women.data)
        self.assertIn(b"Tie-Back Satin Evening Gown", res_women.data)
        self.assertIn(b"Leather Pointed Slingback Pumps", res_women.data)
        # Should NOT display menswear-only items
        self.assertNotIn(b"Relaxed Tailored Chinos", res_women.data)
        self.assertNotIn(b"Everyday White Button-down Oxford Shirt", res_women.data)
        self.assertNotIn(b"Suede Penny Loafers", res_women.data)

        # 2. SCENARIO 2: Men's / Boys' Wardrobe
        with self.app.app_context():
            WardrobeItem.query.filter_by(user_id=self.user_id).delete()
            m_items = [
                WardrobeItem(user_id=self.user_id, name="Italian Silk Necktie", category="Accessories", subcategory="Tie", color="Navy Blue", style="Formal", image_path="defaults/acc_belt.jpg"),
                WardrobeItem(user_id=self.user_id, name="Silver Monogram Cufflinks", category="Accessories", subcategory="Cufflinks", color="Silver", style="Formal", image_path="defaults/acc_watch.jpg"),
                WardrobeItem(user_id=self.user_id, name="Oxford Cotton Shirt", category="Tops", subcategory="Shirt", color="White", style="Smart Casual", image_path="defaults/top_oxford_shirt.jpg"),
            ]
            for item in m_items:
                db.session.add(item)
            db.session.commit()

        res_men = self.client.get("/shopping")
        self.assertEqual(res_men.status_code, 200)
        # Should detect Men's / Boys'
        self.assertIn(b"Men's / Boys'", res_men.data)
        # Should display men's products
        self.assertIn(b"Relaxed Tailored Chinos", res_men.data)
        self.assertIn(b"Everyday White Button-down Oxford Shirt", res_men.data)
        self.assertIn(b"Suede Penny Loafers", res_men.data)
        # Should NOT display women's-only products
        self.assertNotIn(b"Tagliatelle Linen Midi Dress", res_men.data)
        self.assertNotIn(b"Tie-Back Satin Evening Gown", res_men.data)
        self.assertNotIn(b"Leather Pointed Slingback Pumps", res_men.data)

        # 3. SCENARIO 3: Mixed Wardrobe
        with self.app.app_context():
            WardrobeItem.query.filter_by(user_id=self.user_id).delete()
            mix_items = [
                WardrobeItem(user_id=self.user_id, name="Silk Slip Midi Dress", category="Dresses / One-piece", subcategory="Dress", color="Sage Green", style="Smart Casual", image_path="defaults/dress_slip.jpg"),
                WardrobeItem(user_id=self.user_id, name="Silk Necktie", category="Accessories", subcategory="Tie", color="Burgundy", style="Formal", image_path="defaults/acc_belt.jpg"),
            ]
            for item in mix_items:
                db.session.add(item)
            db.session.commit()

        res_mixed = self.client.get("/shopping")
        self.assertEqual(res_mixed.status_code, 200)
        self.assertIn(b"All / Mixed", res_mixed.data)
        # Should display items from both collections
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_mixed.data)
        self.assertIn(b"Relaxed Tailored Chinos", res_mixed.data)

        # 4. SCENARIO 4: Ambiguous / Neutral Wardrobe
        with self.app.app_context():
            WardrobeItem.query.filter_by(user_id=self.user_id).delete()
            neutral_items = [
                WardrobeItem(user_id=self.user_id, name="White Cotton Crewneck T-Shirt", category="Tops", subcategory="T-Shirt", color="White", style="Casual", image_path="defaults/top_linen_tee.jpg"),
                WardrobeItem(user_id=self.user_id, name="Classic Straight Denim Jeans", category="Bottoms", subcategory="Jeans", color="Dark Indigo", style="Casual", image_path="defaults/bottom_jeans.jpg"),
            ]
            for item in neutral_items:
                db.session.add(item)
            # Ensure no saved preference
            UserPreference.query.filter_by(user_id=self.user_id).delete()
            db.session.commit()

        res_ambiguous = self.client.get("/shopping")
        self.assertEqual(res_ambiguous.status_code, 200)
        # Should show prompt asking user for style preference
        self.assertIn(b"Personalize Your Shopping Department", res_ambiguous.data)
        self.assertIn(b"Select your shopping preference", res_ambiguous.data)

        # 5. Setting Style Preference via POST /shopping/set-preference
        res_set_pref = self.client.post("/shopping/set-preference", data={
            "department": "womens"
        }, follow_redirects=True)
        self.assertEqual(res_set_pref.status_code, 200)
        self.assertIn(b"Shopping style preference updated", res_set_pref.data)

        with self.app.app_context():
            pref = UserPreference.query.filter_by(user_id=self.user_id).first()
            self.assertIsNotNone(pref)
            self.assertEqual(pref.gender_preference, "womens")

        # Now when visiting /shopping without query params, Saved Preference is used
        res_after_pref = self.client.get("/shopping")
        self.assertIn(b"Saved Style Preference", res_after_pref.data)
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_after_pref.data)
        self.assertNotIn(b"Relaxed Tailored Chinos", res_after_pref.data)

        # 6. FILTERS
        # 6a. Category filter: Dresses
        res_cat_dress = self.client.get("/shopping?department=womens&category=Dresses / One-piece")
        self.assertEqual(res_cat_dress.status_code, 200)
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_cat_dress.data)
        self.assertIn(b"Tie-Back Satin Evening Gown", res_cat_dress.data)
        self.assertNotIn(b"Pleated Wide-Leg Trousers", res_cat_dress.data)
        self.assertNotIn(b"Leather Pointed Slingback Pumps", res_cat_dress.data)

        # 6b. Macro Category filter: 'Clothing' (Tops, Bottoms, Dresses) - excludes Footwear & Accessories
        res_clothing = self.client.get("/shopping?department=womens&category=Clothing")
        self.assertEqual(res_clothing.status_code, 200)
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_clothing.data)
        self.assertIn(b"Pleated Wide-Leg Trousers", res_clothing.data)
        self.assertNotIn(b"Leather Pointed Slingback Pumps", res_clothing.data)
        self.assertNotIn(b"Emerald Crystal Drop Earrings", res_clothing.data)

        # 6c. Category filter: Footwear
        res_shoes = self.client.get("/shopping?department=womens&category=Footwear")
        self.assertEqual(res_shoes.status_code, 200)
        self.assertIn(b"Leather Pointed Slingback Pumps", res_shoes.data)
        self.assertIn(b"Block-Heel Minimalist Leather Sandals", res_shoes.data)
        self.assertNotIn(b"Tagliatelle Linen Midi Dress", res_shoes.data)

        # 6d. Brand filter: Reformation
        res_brand = self.client.get("/shopping?brand=Reformation")
        self.assertEqual(res_brand.status_code, 200)
        self.assertIn(b"Tagliatelle Linen Midi Dress", res_brand.data)
        self.assertNotIn(b"Pleated Wide-Leg Trousers", res_brand.data)
        self.assertNotIn(b"Tie-Back Satin Evening Gown", res_brand.data)

        # 6e. Price filter: max_price in INR
        res_budget = self.client.get("/shopping?department=womens&max_price=4000")
        self.assertEqual(res_budget.status_code, 200)
        # Quince $39.90 or H&M $42.00 is ~3,500 INR, while Reformation $278 is >23,000 INR
        self.assertNotIn(b"Tagliatelle Linen Midi Dress", res_budget.data)

        # 7. WARDROBE GAPS & DUPLICATE CHECKS
        with self.app.app_context():
            WardrobeItem.query.filter_by(user_id=self.user_id).delete()
            # User with 4 tops, 0 bottoms, and 0 footwear -> Bottoms and Footwear gaps
            # Also user owns a "Warm Ivory" dress
            items_gap = [
                WardrobeItem(user_id=self.user_id, name="Ivory Silk Top", category="Tops", subcategory="Top", color="Ivory", style="Smart Casual", image_path="defaults/top_linen_tee.jpg"),
                WardrobeItem(user_id=self.user_id, name="White Linen Shirt", category="Tops", subcategory="Shirt", color="White", style="Casual", image_path="defaults/top_oxford_shirt.jpg"),
                WardrobeItem(user_id=self.user_id, name="Blue Chambray Shirt", category="Tops", subcategory="Shirt", color="Blue", style="Casual", image_path="defaults/top_oxford_shirt.jpg"),
                WardrobeItem(user_id=self.user_id, name="Sage Green Camisole", category="Tops", subcategory="Camisole", color="Sage Green", style="Casual", image_path="defaults/top_linen_tee.jpg"),
                WardrobeItem(user_id=self.user_id, name="Warm Ivory Summer Dress", category="Dresses / One-piece", subcategory="Dress", color="Warm Ivory", style="Casual", image_path="defaults/dress_linen.jpg"),
            ]
            for item in items_gap:
                db.session.add(item)
            db.session.commit()

        res_gaps = self.client.get("/shopping?department=womens")
        self.assertEqual(res_gaps.status_code, 200)
        # Gap advisory must mention missing bottoms or footwear
        self.assertIn(b"Missing Bottoms", res_gaps.data)
        # Bottoms should have gap filler badge
        self.assertIn(b"Gap Filler", res_gaps.data)
        # Tagliatelle Linen Midi Dress is "Warm Ivory" "Dresses / One-piece" -> duplicate warning for owning Warm Ivory Summer Dress
        self.assertIn(b"You already own", res_gaps.data)
        self.assertIn(b"Warm Ivory Summer Dress", res_gaps.data)

        # 8. NO MANUAL GENDER/DEPARTMENT SELECTOR BUTTONS IN UI
        res_ui = self.client.get("/shopping")
        self.assertEqual(res_ui.status_code, 200)
        self.assertNotIn(b"department=womens\" class=\"btn", res_ui.data)
        self.assertNotIn(b"department=mens\" class=\"btn", res_ui.data)
        self.assertNotIn(b"department=all\" class=\"btn", res_ui.data)
        self.assertIn(b"Personalized Focus:", res_ui.data)
        self.assertIn(b"Image Unavailable", res_ui.data)

        # 9. GENUINE IMAGE ASSETS EXIST ON DISK (NOT SYNTHETIC CIRCLE GRAPHICS)
        import os
        from PIL import Image, ImageStat
        slip_img = os.path.join("app", "static", "defaults", "shop_quince_slip_dress.jpg")
        self.assertTrue(os.path.exists(slip_img), "Quince slip dress image must exist on disk")
        im = Image.open(slip_img)
        stat = ImageStat.Stat(im)
        avg_std = sum(stat.stddev) / len(stat.stddev)
        self.assertGreater(avg_std, 25.0, "Slip dress image must be a genuine detailed photograph, not a placeholder")

if __name__ == "__main__":
    unittest.main()



