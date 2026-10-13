import os
import shutil
import base64
import requests
from PIL import Image
from app.config import Config

MODELS = [
    {
        "id": "alex_studio",
        "name": "Model Alex",
        "pose": "Studio Neutral Front",
        "image": "defaults/model_pose_studio.jpg"
    },
    {
        "id": "jordan_editorial",
        "name": "Model Jordan",
        "pose": "Editorial 3/4 Turn",
        "image": "defaults/model_pose_editorial.jpg"
    },
    {
        "id": "taylor_relaxed",
        "name": "Model Taylor",
        "pose": "Relaxed Stance",
        "image": "defaults/model_pose_relaxed.jpg"
    }
]

def resolve_image_path(base_dir, rel_path):
    """Resolves relative static file paths across defaults and upload folders."""
    if not rel_path:
        return None
    cleaned = rel_path.lstrip("/\\")
    candidates = [
        os.path.join(base_dir, "static", cleaned),
        os.path.join(base_dir, "static", "images", cleaned),
        os.path.join(base_dir, "static", "defaults", os.path.basename(cleaned)),
        os.path.join(base_dir, "static", "images", "defaults", os.path.basename(cleaned)),
        os.path.join(base_dir, cleaned),
        cleaned if os.path.isabs(cleaned) else None,
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def prepare_image_for_inference(img_path, max_dim=1024, is_garment=False):
    """
    Standardizes input images to RGB JPEG within diffusion resolution bounds.
    Returns path to temporary standardized file.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(base_dir, "static", "uploads", "inference_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    file_prefix = "temp_garm_" if is_garment else "temp_person_"
    clean_stem = "".join([c if c.isalnum() else "_" for c in os.path.splitext(os.path.basename(img_path))[0]])
    temp_filename = f"{file_prefix}{clean_stem}.jpg"
    temp_path = os.path.join(temp_dir, temp_filename)

    with Image.open(img_path) as im:
        rgb_im = im.convert("RGB")
        w, h = rgb_im.size
        if max(w, h) > max_dim:
            if w >= h:
                new_w = max_dim
                new_h = int(h * (max_dim / float(w)))
            else:
                new_h = max_dim
                new_w = int(w * (max_dim / float(h)))
            rgb_im = rgb_im.resize((new_w, new_h), Image.Resampling.LANCZOS)
        rgb_im.save(temp_path, "JPEG", quality=92)
    
    return temp_path

def generate_lower_body_mask(person_img_path, is_personal_photo=False):
    """
    Generates a tailored binary mask targeting the lower body (waistband to ankles).
    Returns the absolute path to the generated mask PNG.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(base_dir, "static", "uploads", "inference_temp")
    os.makedirs(temp_dir, exist_ok=True)
    mask_filename = f"mask_lower_{os.path.basename(person_img_path)}.png"
    mask_path = os.path.join(temp_dir, mask_filename)

    with Image.open(person_img_path) as im:
        w, h = im.size
        mask = Image.new("L", (w, h), 0)

        # Proportions:
        # Waist / hips start around 48% to 50% of height
        # Ankles / cuffs end around 90% to 92% of height
        y_start = int(h * 0.50) if is_personal_photo else int(h * 0.48)
        y_end = int(h * 0.90) if is_personal_photo else int(h * 0.92)
        x_start = int(w * 0.28)
        x_end = int(w * 0.72)

        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                mask.putpixel((x, y), 255)

        # Save as RGB PNG for IDM-VTON layers compatibility
        mask.convert("RGB").save(mask_path)

    return mask_path

def generate_dress_mask(person_img_path, is_personal_photo=False):
    """
    Generates a tailored full-garment binary mask covering the person from neckline
    down to hem/ankles (replacing both upper and lower preexisting garments, e.g.
    shorts, jeans, or trousers) for one-piece dresses, gowns, frocks, and lehengas.
    Returns the absolute path to the generated mask PNG.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    temp_dir = os.path.join(base_dir, "static", "uploads", "inference_temp")
    os.makedirs(temp_dir, exist_ok=True)
    mask_filename = f"mask_dress_{os.path.basename(person_img_path)}.png"
    mask_path = os.path.join(temp_dir, mask_filename)

    with Image.open(person_img_path) as im:
        w, h = im.size
        mask = Image.new("L", (w, h), 0)

        if not is_personal_photo:
            # Studio models (Alex, Jordan, Taylor):
            # Head and neck end around 25% of height; ankles/feet end around 88% of height.
            y_start = int(h * 0.25)
            y_end = int(h * 0.88)
            x_start = int(w * 0.18)
            x_end = int(w * 0.82)
        else:
            # Personal photos:
            # In taller portrait shots (e.g. 9:16 or full-room photos), the person has vertical headroom.
            # Smoothly adapt y_start based on aspect ratio while ensuring the neckline is protected.
            ar = w / float(h)
            y_start_ratio = 0.25 + max(0.0, min(0.18, (0.67 - ar) * 0.80))
            y_start = int(h * y_start_ratio)
            y_end = int(h * 0.88)
            x_start = int(w * 0.18)
            x_end = int(w * 0.82)

        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                mask.putpixel((x, y), 255)

        # Save as RGB PNG for IDM-VTON layers compatibility
        mask.convert("RGB").save(mask_path)

    return mask_path

def is_dress_item(item):
    """Detects whether an outfit garment is a full one-piece dress, gown, frock, or lehenga."""
    if not item:
        return False
    cat = (getattr(item, 'category', '') or '').lower()
    name = (getattr(item, 'name', '') or '').lower()
    keywords = ["dress", "one-piece", "one piece", "gown", "frock", "lehenga", "anarkali", "saree", "sari", "jumpsuit", "romper"]
    return any(k in cat for k in keywords) or any(k in name for k in keywords)

def run_idm_vton_inference(person_img_path, garment_img_path, garment_desc, output_filename, is_lower_body=False, is_dress=False, is_personal_photo=False):
    """
    Runs neural diffusion virtual try-on inference using IDM-VTON.
    Supports Upper-body (automatic openpose/parsing mask),
    Lower-body (custom binary mask for pants, chinos, skirts, jeans),
    and One-piece Dresses (custom full-length mask covering neckline to hem/ankles).
    Returns (result_abs_path, error_message).
    """
    try:
        from gradio_client import Client, handle_file
        from dotenv import load_dotenv
        load_dotenv(override=True)
    except ImportError:
        return None, "gradio_client package is not installed."

    hf_token = os.environ.get("HF_TOKEN") or getattr(Config, "HF_TOKEN", None)

    try:
        prep_person = prepare_image_for_inference(person_img_path, max_dim=1024, is_garment=False)
        prep_garment = prepare_image_for_inference(garment_img_path, max_dim=1024, is_garment=True)

        layers = []
        use_auto_mask = True

        if is_dress:
            mask_file = generate_dress_mask(prep_person, is_personal_photo=is_personal_photo)
            layers = [handle_file(mask_file)]
            use_auto_mask = False
        elif is_lower_body:
            mask_file = generate_lower_body_mask(prep_person, is_personal_photo=is_personal_photo)
            layers = [handle_file(mask_file)]
            use_auto_mask = False

        if is_dress:
            clean_desc = garment_desc or "full length one-piece dress gown frock lehenga"
        elif is_lower_body:
            clean_desc = garment_desc or "tailored pants trousers"
        else:
            clean_desc = garment_desc or "fashion garment"

        candidate_spaces = [
            os.environ.get("VTON_HF_SPACE", "yisol/IDM-VTON"),
            "Nymbo/Virtual-Try-On"
        ]

        # Prioritize space with user token, falling back to anonymous pool if ZeroGPU token quota is hit
        attempts = []
        for space_id in candidate_spaces:
            if hf_token:
                attempts.append((space_id, hf_token))
            attempts.append((space_id, None))

        last_error = None
        for space_id, tok in attempts:
            try:
                client = Client(space_id, token=tok) if tok else Client(space_id)
                result = client.predict(
                    dict={"background": handle_file(prep_person), "layers": layers, "composite": None},
                    garm_img=handle_file(prep_garment),
                    garment_des=clean_desc,
                    is_checked=use_auto_mask,
                    is_checked_crop=False,
                    denoise_steps=20,
                    seed=42,
                    api_name="/tryon"
                )

                if result and len(result) > 0 and result[0] and os.path.exists(result[0]):
                    return result[0], None

                last_error = f"{space_id} completed but returned no output image."
            except Exception as ex:
                err_str = str(ex)
                if "ZeroGPU quota" in err_str:
                    last_error = f"Hugging Face ZeroGPU quota limit reached on {space_id} (token: {'provided' if tok else 'anonymous'})."
                    continue
                elif "timeout" in err_str.lower():
                    last_error = f"Virtual try-on request timed out on {space_id} remote GPU queue."
                else:
                    last_error = f"Inference error on {space_id}: {err_str}"

        # If IDM-VTON failed for dress, try OOTDiffusion as high-quality fallback
        if is_dress:
            ootd_res, ootd_err = run_ootd_inference(prep_person, prep_garment, category="Dress")
            if ootd_res and os.path.exists(ootd_res):
                return ootd_res, None

        return None, last_error

    except Exception as ex:
        return None, f"Image preparation error: {str(ex)}"

def run_ootd_inference(person_img_path, garment_img_path, category="Lower-body"):
    """
    Optional secondary fallback using OOTDiffusion on ZeroGPU.
    Supports: 'Upper-body', 'Lower-body', 'Dress'.
    Returns (result_abs_path, error_message).
    """
    try:
        from gradio_client import Client, handle_file
    except ImportError:
        return None, "gradio_client package is not installed."

    hf_token = os.environ.get("HF_TOKEN") or getattr(Config, "HF_TOKEN", None)

    try:
        prep_person = prepare_image_for_inference(person_img_path, max_dim=1024, is_garment=False)
        prep_garment = prepare_image_for_inference(garment_img_path, max_dim=1024, is_garment=True)

        client = Client("levihsu/OOTDiffusion", token=hf_token) if hf_token else Client("levihsu/OOTDiffusion")
        res = client.predict(
            vton_img=handle_file(prep_person),
            garm_img=handle_file(prep_garment),
            category=category,
            n_samples=1,
            n_steps=20,
            image_scale=2.0,
            seed=-1,
            api_name="/process_dc"
        )

        if res and len(res) > 0 and res[0].get("image") and os.path.exists(res[0]["image"]):
            return res[0]["image"], None

        return None, "OOTDiffusion completed but returned no output image."

    except Exception as ex:
        err_str = str(ex)
        if "ZeroGPU quota" in err_str:
            clean_err = "Hugging Face ZeroGPU quota reached. Please check your HF_TOKEN in .env."
        elif "timeout" in err_str.lower():
            clean_err = "Lower-body try-on request timed out on the remote GPU queue."
        else:
            clean_err = f"Lower-body try-on error: {err_str}"
        return None, clean_err

def execute_full_ensemble_tryon(person_img_path, outfit_items, output_filename, is_personal_photo=False, user_approved=True):
    """
    Applies both Tops and Bottoms (or full One-piece Dresses) to the person
    using real neural diffusion models.
    Returns (preview_rel_path, note_text, error_message).
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if not person_img_path or not os.path.exists(person_img_path):
        return None, None, "Person image could not be located on the server."

    items_list = [i for i in outfit_items if i is not None]
    if not items_list:
        return None, None, "No wardrobe garments selected for virtual try-on."

    # Identify individual garments from closet ensemble
    dress_item = next((i for i in items_list if is_dress_item(i)), None)
    top_item = next((i for i in items_list if i.category == "Tops" and not is_dress_item(i)), None)
    bottom_item = next((i for i in items_list if i.category == "Bottoms" and not is_dress_item(i)), None)

    # If neither dress, top, nor bottom is found by standard category, check primary
    if not dress_item and not top_item and not bottom_item:
        if is_dress_item(items_list[0]):
            dress_item = items_list[0]
        else:
            top_item = items_list[0]

    # Privacy Protection
    if is_personal_photo and not user_approved:
        return None, None, (
            "Privacy Protection: Your personal photo cannot be processed remotely without your approval. "
            "Please check the approval box to permit processing via the neural try-on service."
        )

    out_dir = os.path.join(base_dir, "static", "uploads")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, output_filename)

    # -------------------------------------------------------------
    # CASE 1: ONE-PIECE DRESS
    # -------------------------------------------------------------
    if dress_item:
        dress_path = resolve_image_path(base_dir, dress_item.image_path)
        if not dress_path or not os.path.exists(dress_path):
            return None, None, f"Garment image for '{dress_item.name}' could not be located."

        desc = f"{dress_item.name} ({getattr(dress_item, 'color', '')} full-length one-piece dress)"
        gen_path, err = run_idm_vton_inference(
            person_img_path, dress_path, desc, output_filename,
            is_lower_body=False, is_dress=True, is_personal_photo=is_personal_photo
        )

        if gen_path and os.path.exists(gen_path):
            shutil.copyfile(gen_path, out_path)
            note = f"Neural Virtual Try-On: Applied '{dress_item.name}' (One-piece Dress)."
            return f"uploads/{output_filename}", note, None
        return None, None, err or "Failed to generate dress try-on."

    # -------------------------------------------------------------
    # CASE 2: TWO-PIECE ENSEMBLE (TOP + BOTTOM)
    # -------------------------------------------------------------
    if top_item and bottom_item:
        top_path = resolve_image_path(base_dir, top_item.image_path)
        bottom_path = resolve_image_path(base_dir, bottom_item.image_path)

        if not top_path or not os.path.exists(top_path):
            return None, None, f"Garment image for top '{top_item.name}' could not be located."
        if not bottom_path or not os.path.exists(bottom_path):
            return None, None, f"Garment image for bottom '{bottom_item.name}' could not be located."

        top_desc = f"{top_item.name} ({getattr(top_item, 'color', '')} top)"
        bottom_desc = f"{bottom_item.name} ({getattr(bottom_item, 'color', '')} pants/bottom)"

        # Step 1: Inpaint Top on person
        step1_img, err1 = run_idm_vton_inference(
            person_img_path, top_path, top_desc, f"step1_{output_filename}",
            is_lower_body=False, is_personal_photo=is_personal_photo
        )
        if not step1_img or not os.path.exists(step1_img):
            return None, None, f"Top garment try-on failed: {err1}"

        # Step 2: Inpaint Bottom onto the person now wearing the top
        step2_img, err2 = run_idm_vton_inference(
            step1_img, bottom_path, bottom_desc, f"step2_{output_filename}",
            is_lower_body=True, is_personal_photo=is_personal_photo
        )
        if step2_img and os.path.exists(step2_img):
            shutil.copyfile(step2_img, out_path)
            note = f"Full Outfit Neural Try-On: Applied '{top_item.name}' (Top) and '{bottom_item.name}' (Bottom)."
            return f"uploads/{output_filename}", note, None

        # If step 2 fails, report error honestly so user knows exactly what failed
        return None, None, f"Lower-body try-on failed for '{bottom_item.name}': {err2}"

    # -------------------------------------------------------------
    # CASE 3: BOTTOM ONLY
    # -------------------------------------------------------------
    if bottom_item and not top_item:
        bottom_path = resolve_image_path(base_dir, bottom_item.image_path)
        if not bottom_path or not os.path.exists(bottom_path):
            return None, None, f"Garment image for bottom '{bottom_item.name}' could not be located."

        bottom_desc = f"{bottom_item.name} ({getattr(bottom_item, 'color', '')} pants/bottom)"
        gen_path, err = run_idm_vton_inference(
            person_img_path, bottom_path, bottom_desc, output_filename,
            is_lower_body=True, is_personal_photo=is_personal_photo
        )
        if gen_path and os.path.exists(gen_path):
            shutil.copyfile(gen_path, out_path)
            note = f"Neural Virtual Try-On: Applied '{bottom_item.name}' (Bottom)."
            return f"uploads/{output_filename}", note, None
        return None, None, err or "Failed to generate bottom try-on."

    # -------------------------------------------------------------
    # CASE 4: TOP ONLY
    # -------------------------------------------------------------
    if top_item:
        top_path = resolve_image_path(base_dir, top_item.image_path)
        if not top_path or not os.path.exists(top_path):
            return None, None, f"Garment image for top '{top_item.name}' could not be located."

        top_desc = f"{top_item.name} ({getattr(top_item, 'color', '')} top)"
        gen_path, err = run_idm_vton_inference(
            person_img_path, top_path, top_desc, output_filename,
            is_lower_body=False, is_personal_photo=is_personal_photo
        )
        if gen_path and os.path.exists(gen_path):
            shutil.copyfile(gen_path, out_path)
            note = f"Neural Virtual Try-On: Applied '{top_item.name}' (Top)."
            return f"uploads/{output_filename}", note, None
        return None, None, err or "Failed to generate top try-on."

    return None, None, "No compatible clothing garments found in the selected outfit."

def render_model_tryon(model_id, outfit_items, output_filename):
    """
    Renders full outfit virtual try-on on an AI Model (Alex, Jordan, or Taylor)
    using the exact selected clothing images from the closet.
    Applies both tops and bottoms when an ensemble is selected.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_info = next((m for m in MODELS if m["id"] == model_id), MODELS[0])
    model_img_path = resolve_image_path(base_dir, model_info["image"])

    return execute_full_ensemble_tryon(
        person_img_path=model_img_path,
        outfit_items=outfit_items,
        output_filename=output_filename,
        is_personal_photo=False,
        user_approved=True
    )

def process_user_photo_tryon(user_photo_path, outfit_items, output_filename, user_approved=True):
    """
    Applies the full selected clothing combination (both tops and bottoms)
    to the user's uploaded photograph using real neural diffusion models.
    """
    return execute_full_ensemble_tryon(
        person_img_path=user_photo_path,
        outfit_items=outfit_items,
        output_filename=output_filename,
        is_personal_photo=True,
        user_approved=user_approved
    )
