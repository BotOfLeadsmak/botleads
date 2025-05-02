import json
import os
import time
import hashlib
import requests
from datetime import datetime
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image
from io import BytesIO

# === CONFIGURAÇÕES ===
TOKEN = "7283344497:AAHX_-L_PDPvDME3gXxl-vUh4viNqOWHiXg"
ADMIN = [7363883967]
CANAL_ID = -1001984009490
APP_ID = "18381520002"
SECRET = "OBSJ45U4BKTSCNH7OSWCTZPNBKYB5RHU"
ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"
HISTORICO_JSON = "enviados.json"
TEMPLATE_PATH = "template/template.png"

bot = TeleBot(TOKEN)
scheduler = BackgroundScheduler()
scheduler.start()
onoff = False


# === FUNÇÕES AUXILIARES ===
def saudacao():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "🌞 Bom dia!"
    elif 12 <= hora < 18:
        return "☀️ Boa tarde!"
    else:
        return "🌙 Boa noite!"

def carregar_ids_enviados():
    if os.path.exists(HISTORICO_JSON):
        with open(HISTORICO_JSON, "r") as f:
            return set(json.load(f))
    return set()

def salvar_ids_enviados(ids):
    with open(HISTORICO_JSON, "w") as f:
        json.dump(list(ids), f)

def gerar_imagem_personalizada(url_imagem_produto, nome_arquivo_saida='oferta.jpg'):
    template = Image.open(TEMPLATE_PATH).convert("RGBA")
    response = requests.get(url_imagem_produto)
    imagem_produto = Image.open(BytesIO(response.content)).convert("RGBA")
    imagem_produto = imagem_produto.resize((630, 630))
    template.paste(imagem_produto, (220, 170), imagem_produto)
    os.makedirs('temp', exist_ok=True)
    caminho = f"temp/{nome_arquivo_saida}"
    template.convert("RGB").save(caminho, format="JPEG")
    return caminho

def buscar_nova_oferta(ids_enviados):
    query = """
    query {
      productOfferV2(page: 1, limit: 20, sortType: 5) {
        nodes {
          itemId
          productName
          commissionRate
          offerLink
          imageUrl
          priceMin
          priceMax
        }
      }
    }
    """
    payload = json.dumps({"query": query})
    timestamp = str(int(time.time()))
    raw = APP_ID.strip() + timestamp + payload + SECRET.strip()
    assinatura = hashlib.sha256(raw.encode()).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"SHA256 Credential={APP_ID.strip()}, Timestamp={timestamp}, Signature={assinatura}"
    }

    response = requests.post(ENDPOINT, headers=headers, data=payload)

    try:
        data = response.json()
        nodes = data["data"]["productOfferV2"]["nodes"]
    except (KeyError, TypeError):
        print("❌ ERRO NA RESPOSTA DA API SHOPEE:")
        print("Status:", response.status_code)
        print("Texto:", response.text)
        return None

    for item in nodes:
        if item["itemId"] not in ids_enviados:
            return item

    return None

def enviar_oferta_para_canal():
    ids_enviados = carregar_ids_enviados()
    oferta = buscar_nova_oferta(ids_enviados)
    if not oferta:
        return

    nome = oferta["productName"]
    preco_original = float(oferta["priceMax"])
    preco_oferta = float(oferta["priceMin"])
    link = oferta["offerLink"]
    imagem = oferta["imageUrl"]
    item_id = oferta["itemId"]

    imagem_final = gerar_imagem_personalizada(imagem)

    legenda = (
        f"📢 *OFERTA IMPERDÍVEL!* \n\n"
        f"🛍️ *Produto:*  `{nome}`\n\n"
        f"❌ De: *R$ {preco_original:,.2f}*\n"
        f"✅ Agora por: *R$ {preco_oferta:,.2f}*\n\n"
        f"🔥 *Descontos exclusivos só hoje!*\n\n"
        f"🎯 Estoque limitado, aproveite agora!\n"
        f"🔗 [🚀 COMPRAR AGORA]({link})\n\n"
        f"⚠ _Promoção sujeita à alteração de preço e estoque do site._"
    )

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔗 COMPRAR AGORA 🚀", url=link))

    bot.send_photo(CANAL_ID, open(imagem_final, "rb"), caption=legenda, parse_mode="Markdown", reply_markup=markup)
    ids_enviados.add(item_id)
    salvar_ids_enviados(ids_enviados)

def iniciar_disparo_automatico():
    enviar_oferta_para_canal()
    scheduler.add_job(enviar_oferta_para_canal, "interval", minutes=15, id="envio_ofertas", replace_existing=True)

def parar_disparo_automatico():
    if scheduler.get_job("envio_ofertas"):
        scheduler.remove_job("envio_ofertas")

@bot.message_handler(commands=["start"])
def start(message):
    global onoff
    chat_id = message.chat.id

    if message.from_user.id in ADMIN:
        markup = InlineKeyboardMarkup()
        estado_botao = "✅ BOT ON" if onoff else "❌ BOT OFF"
        markup.add(
            InlineKeyboardButton("📜 STATUS", callback_data="status"),
            InlineKeyboardButton(estado_botao, callback_data="LIGADELISGA")
        )
        try:
            bot.send_sticker(chat_id, "CAACAgEAAxkBAAEOZrdoFNepT_LIclryxpPKxfbf9dsXDAACbgQAAqDqqES1XlWnhwlpAzYE")
        except:
            pass
        time.sleep(1)
        bot.send_message(chat_id,
            f"🔍 Olá {message.from_user.first_name}, {saudacao()}\nAcesse o *Painel Administrativo* abaixo:",
            parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"👋 Olá {message.from_user.first_name}, {saudacao()}")

@bot.callback_query_handler(func=lambda call: call.data == "LIGADELISGA")
def alternar_estado_bot(call):
    global onoff
    chat_id = call.message.chat.id
    onoff = not onoff
    novo_estado = "✅ BOT ON" if onoff else "❌ BOT OFF"

    try:
        bot.answer_callback_query(call.id, f"Status alterado para {novo_estado}")
    except:
        pass

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📜 STATUS", callback_data="status"),
        InlineKeyboardButton(novo_estado, callback_data="LIGADELISGA")
    )

    try:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markup)
    except:
        pass

    if onoff:
        iniciar_disparo_automatico()
    else:
        parar_disparo_automatico()

bot.infinity_polling()
