from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

load_dotenv()
genai.configure(api_key=os.getenv("API_KEY"))

app = Flask(__name__)
CORS(app)

MAX_PALABRAS = 24000
MIN_PALABRAS = 20
UMBRAL_RESUMEN = 400

def home():
    return jsonify({"message": "Backend activo"}), 200

def contar_palabras(texto):
    return len(texto.strip().split())

def validar_texto(texto):
    if not texto or not texto.strip():
        return False, "No se recibió ningún texto."
    if contar_palabras(texto) < MIN_PALABRAS:
        return False, f"El texto es demasiado corto. Mínimo {MIN_PALABRAS} palabras."
    if contar_palabras(texto) > MAX_PALABRAS:
        return False, f"El texto es demasiado largo. Máximo {MAX_PALABRAS} palabras."
    return True, None

def truncar_a_350_palabras(texto):
    palabras = texto.split()
    if len(palabras) > 350:
        return ' '.join(palabras[:350]) + "..."
    return texto

def extraer_resumen_e_ideas(respuesta_texto):
    lineas = [linea.strip() for linea in respuesta_texto.strip().split("\n") if linea.strip()]
    resumen = []
    ideas = []
    en_ideas = False

    for linea in lineas:
        if not en_ideas and (
            "ideas principales" in linea.lower() or
            linea.startswith("1.") or
            linea.startswith("- 1.") or
            linea.startswith("1 ") or
            re.match(r"^(\*|-|\d+\.)\s+", linea)
        ):
            en_ideas = True

        if en_ideas:
            if re.match(r"^(\*|-|\d+\.)\s+", linea):
                ideas.append(re.sub(r"^(\*|-|\d+\.)\s*", "", linea).strip())
            else:
                ideas.append(linea.strip())
        else:
            resumen.append(linea.strip())

    resumen_final = ' '.join(resumen).strip()
    return resumen_final, ideas


@app.route("/resumir", methods=["POST"])
def resumir():
    try:
        data = request.get_json()
        texto = data.get("texto", "")

        es_valido, mensaje = validar_texto(texto)
        if not es_valido:
            return jsonify({"error": mensaje}), 400

        if contar_palabras(texto) > UMBRAL_RESUMEN:
            modelo = genai.GenerativeModel("gemini-2.0-flash")
            prompt = (
                "Resume el siguiente texto en menos de 250 palabras sin perder el significado esencial. "
                "Después, dame 5 ideas principales del texto. No coloques encabezados como 'Resumen' ni 'Ideas principales':\n\n"
                f"{texto}"
            )
            respuesta = modelo.generate_content(prompt)

            if hasattr(respuesta, "text") and respuesta.text.strip():
                respuesta_texto = respuesta.text.strip()
                resumen, ideas_principales = extraer_resumen_e_ideas(respuesta_texto)
                resumen_truncado = truncar_a_350_palabras(resumen)

                return jsonify({
                    "resumen": resumen_truncado,
                    "ideas_principales": ideas_principales
                })
            else:
                return jsonify({"error": "No se pudo generar un resumen válido."}), 500

        return jsonify({"resumen": texto.strip(), "ideas_principales": []})

    except Exception as e:
        return jsonify({"error": f"Ocurrió un error: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Servidor corriendo en http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
