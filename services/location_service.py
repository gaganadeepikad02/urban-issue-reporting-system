from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from geopy.geocoders import Nominatim


def get_exif_location(image_path):

    try:

        with Image.open(image_path) as img:

            try:
                exif = img._getexif()
            except Exception:
                return None, None

            if not exif:
                return None, None

            gps_info = {}

            try:
                for tag, value in exif.items():

                    decoded = TAGS.get(tag)

                    if decoded == "GPSInfo":

                        for t in value:
                            sub_decoded = GPSTAGS.get(t)
                            gps_info[sub_decoded] = value[t]
            except Exception:
                return None, None

            if not gps_info:
                return None, None

            def convert(coord):

                try:

                    def to_float(x):

                        try:
                            if isinstance(x, tuple):
                                return x[0] / x[1]
                            return float(x)

                        except Exception:
                            return float(x)

                    d = to_float(coord[0])
                    m = to_float(coord[1])
                    s = to_float(coord[2])

                    return d + (m / 60.0) + (s / 3600.0)

                except Exception:
                    raise Exception("Failed to convert GPS coordinate")

            try:
                lat = convert(gps_info["GPSLatitude"])
                lon = convert(gps_info["GPSLongitude"])
            except Exception:
                return None, None

            try:
                if gps_info.get("GPSLatitudeRef") != "N":
                    lat = -lat

                if gps_info.get("GPSLongitudeRef") != "E":
                    lon = -lon
            except Exception:
                return None, None

            return lat, lon

    except Exception:
        return None, None


def reverse_geocode(lat, lon):

    try:

        if lat is None or lon is None:
            return {}

        geolocator = Nominatim(
            user_agent="urbaneye",
            timeout=5
        )

        try:
            location = geolocator.reverse(
                (lat, lon),
                language="en"
            )
        except Exception:
            return {}

        if not location:
            return {}

        try:
            addr = location.raw.get("address", {})
        except Exception:
            addr = {}

        return {
            "street":
                addr.get("road")
                or addr.get("pedestrian")
                or addr.get("neighbourhood")
                or "",

            "locality":
                addr.get("suburb")
                or addr.get("neighbourhood")
                or addr.get("village")
                or "",

            "postal_code":
                addr.get("postcode", ""),

            "district":
                addr.get("city_district")
                or addr.get("city")
                or addr.get("county")
                or "",

            "state":
                addr.get("state", ""),

            "country":
                addr.get("country", "")
        }

    except Exception:
        return {}
