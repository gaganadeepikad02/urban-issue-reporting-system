import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(file_path):
    try:
        result = cloudinary.uploader.upload(file_path)
        return result["secure_url"]
    except Exception as e:
        raise Exception(f"Cloudinary upload failed: {str(e)}")
