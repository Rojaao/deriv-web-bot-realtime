
import streamlit as st
import websocket
import json
import time
import threading

st.set_page_config(page_title="Robô Deriv - BOTGPT", layout="centered")
st.title("🤖 Robô Deriv com WebSocket - BOTGPT")

token = st.text_input("🔐 Insira seu token da Deriv", type="password")
valor_inicial = st.number_input("💵 Valor Inicial", value=0.35, step=0.01)
fator_martingale = st.number_input("📈 Fator Martingale", value=1.65)
limite_lucro = st.number_input("✅ Limite de Lucro ($)", value=10.0)
limite_perda = st.number_input("❌ Limite de Perda ($)", value=10.0)
usar_martingale = st.checkbox("🎯 Usar Martingale", value=True)
operacao = st.selectbox("📊 Tipo de operação", ["CALL", "PUT"])
iniciar = st.button("🚀 Iniciar Robô")

log = st.empty()

def deriv_bot_real(token, stake, usar_martingale, fator_martingale, limite_lucro, limite_perda, operacao):
    lucro_total = 0
    perda_total = 0
    entrada = stake

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect("wss://ws.derivws.com/websockets/v3?app_id=1089")

            ws.send(json.dumps({"authorize": token}))
            ws.recv()

            proposal_type = "CALL" if operacao == "CALL" else "PUT"

            ws.send(json.dumps({
                "proposal": 1,
                "amount": entrada,
                # "barrier": "+0.1" if proposal_type == "CALL" else "-0.1",
                "basis": "stake",
                "contract_type": proposal_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "t",
                "symbol": "R_10"
            }))

            data = json.loads(ws.recv())
            if "proposal" not in data:
                log.error("Erro ao obter proposta.")
                break

            proposal_id = data["proposal"]["id"]
            ws.send(json.dumps({"buy": proposal_id, "price": entrada}))
            buy_response = json.loads(ws.recv())

            if "buy" not in buy_response:
                log.error("Erro ao comprar contrato.")
                break

            log.info(f"💰 Entrada: ${entrada:.2f} | Tipo: {proposal_type}")

            while True:
                result = json.loads(ws.recv())
                if "transaction_id" in result:
                    continue
                if "buy" in result or "profit" in str(result):
                    break

            if "profit" in str(result):
                profit = float(result.get("profit", entrada))
                lucro_total += profit
                perda_total = 0
                log.success(f"✅ Ganhou ${profit:.2f} | Lucro Total: ${lucro_total:.2f}")
                entrada = stake
            else:
                perda_total += entrada
                log.warning(f"❌ Perdeu ${entrada:.2f} | Perda Acumulada: ${perda_total:.2f}")
                entrada = entrada * fator_martingale if usar_martingale else stake

            if lucro_total >= limite_lucro:
                log.success("🎯 Limite de lucro atingido. Robô finalizado.")
                break
            if perda_total >= limite_perda:
                log.error("🛑 Limite de perda atingido. Robô finalizado.")
                break

            ws.close()
            time.sleep(2)
        except Exception as e:
            log.error(f"Erro: {e}")
            break

if iniciar:
    if token:
        t = threading.Thread(target=deriv_bot_real, args=(
            token, valor_inicial, usar_martingale,
            fator_martingale, limite_lucro, limite_perda, operacao))
        t.start()
    else:
        st.error("🔑 Por favor, insira seu token da Deriv.")
