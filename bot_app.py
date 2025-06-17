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

log_area = st.empty()

def deriv_bot_real(token, stake, usar_martingale, fator_martingale, limite_lucro, limite_perda, operacao):
    lucro_total = 0
    perda_total = 0
    entrada = stake

    while True:
        try:
            ws = websocket.WebSocket()
            ws.connect("wss://ws.derivws.com/websockets/v3?app_id=1089")

            ws.send(json.dumps({"authorize": token}))
            response = json.loads(ws.recv())
            if "error" in response:
                log_area.error(f"Erro ao autorizar: {response['error']['message']}")
                break

            log_area.info("✅ Conectado e autorizado com sucesso.")

            proposal_type = "CALL" if operacao == "CALL" else "PUT"

            ws.send(json.dumps({
                "proposal": 1,
                "amount": entrada,
                "barrier": "+0.1" if proposal_type == "CALL" else "-0.1",
                "basis": "stake",
                "contract_type": proposal_type,
                "currency": "USD",
                "duration": 1,
                "duration_unit": "t",
                "symbol": "R_100"
            }))

            proposal = json.loads(ws.recv())
            if "error" in proposal:
                log_area.error(f"Erro na proposta: {proposal['error']['message']}")
                break

            proposal_id = proposal["proposal"]["id"]
            ws.send(json.dumps({"buy": proposal_id, "price": entrada}))
            buy_response = json.loads(ws.recv())

            if "error" in buy_response:
                log_area.error(f"Erro ao comprar: {buy_response['error']['message']}")
                break

            log_area.info(f"📈 Operação iniciada - {proposal_type} com ${entrada:.2f}")

            # Aguardando resultado
            result = json.loads(ws.recv())
            if "error" in result:
                log_area.error(f"Erro no resultado: {result['error']['message']}")
                break

            if "buy" in result and "contract_id" in result["buy"]:
                contract_id = result["buy"]["contract_id"]
                log_area.info(f"🆔 Contrato ativo: {contract_id}")
            
            # Verificando resultado do contrato
            while True:
                update = json.loads(ws.recv())
                if "profit" in update:
                    profit = float(update["profit"])
                    if profit > 0:
                        lucro_total += profit
                        perda_total = 0
                        entrada = stake
                        log_area.success(f"✅ Ganhou ${profit:.2f} | Lucro Total: ${lucro_total:.2f}")
                    else:
                        perda_total += entrada
                        log_area.warning(f"❌ Perdeu ${entrada:.2f} | Perda Acumulada: ${perda_total:.2f}")
                        entrada = entrada * fator_martingale if usar_martingale else stake
                    break

            if lucro_total >= limite_lucro:
                log_area.success("🎯 Limite de lucro atingido. Robô finalizado.")
                break
            if perda_total >= limite_perda:
                log_area.error("🛑 Limite de perda atingido. Robô finalizado.")
                break

            ws.close()
            time.sleep(2)

        except Exception as e:
            log_area.error(f"Erro inesperado: {str(e)}")
            break

if iniciar:
    if token:
        thread = threading.Thread(target=deriv_bot_real, args=(
            token, valor_inicial, usar_martingale, fator_martingale,
            limite_lucro, limite_perda, operacao))
        thread.start()
    else:
        st.warning("⚠️ Por favor, insira seu token Deriv.")
