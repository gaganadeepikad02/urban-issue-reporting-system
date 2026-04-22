try:
    import tflite_runtime.interpreter as tflite
    print("Using tflite-runtime")
except ImportError:
    import tensorflow as tf
    print("Using TensorFlow")
import numpy as np
import json
from PIL import Image


MODEL_PATH = "model.tflite"
LABELS_PATH = "labels.json"

CONFIDENCE_THRESHOLD = 0.70


try:
    interpreter = tflite.Interpreter(model_path=MODEL_PATH)
except NameError:
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
except Exception as e:
    raise Exception(f"Failed to load TFLite model: {str(e)}")


try:
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
except Exception as e:
    raise Exception(f"Failed to read model tensor details: {str(e)}")


try:
    with open(LABELS_PATH) as f:
        labels = json.load(f)
except Exception as e:
    raise Exception(f"Failed to load labels.json: {str(e)}")


try:
    if isinstance(labels, dict):

        if all(isinstance(v, int) for v in labels.values()):
            labels = list(labels.keys())
        else:
            labels = list(labels.values())

except Exception as e:
    raise Exception(f"Invalid labels format: {str(e)}")


def predict(image_path):

    try:

        height = input_details[0]['shape'][1]
        width = input_details[0]['shape'][2]

        try:
            with Image.open(image_path) as img:

                img = img.convert("RGB").resize((width, height))

                img = np.array(img) / 255.0
                img = np.expand_dims(img, axis=0).astype(np.float32)

        except Exception:
            raise Exception("Image preprocessing failed")

        try:
            interpreter.set_tensor(
                input_details[0]['index'], img
            )

            interpreter.invoke()

        except Exception:
            raise Exception("Model inference failed")

        try:
            output = interpreter.get_tensor(
                output_details[0]['index']
            )[0]
        except Exception:
            raise Exception("Failed to read model output")

        idx = int(np.argmax(output))
        confidence = float(output[idx])

        if idx >= len(labels):
            raise Exception(
                "Model index exceeds labels"
            )

        category = labels[idx]

        if isinstance(category, str):
            category = category.title()

        return category, confidence

    except Exception as e:
        raise Exception(f"Prediction error: {str(e)}")
