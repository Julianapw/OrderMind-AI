import html
import json
import os
import re

import requests
import streamlit as st


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="OrderMind AI",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000/api/v1",
).rstrip("/")


# ============================================================
# ESTILIZAÇÃO
# ============================================================

st.markdown(
    """
    <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
        );

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background-color: #F3F6F8;
        }

        [data-testid="stSidebar"] {
            background-color: #173B57;
        }

        [data-testid="stSidebar"] * {
            color: #FFFFFF;
        }

        [data-testid="stSidebar"] .stRadio label {
            color: #FFFFFF;
        }

        .main-title {
            color: #173B57;
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .subtitle {
            color: #64748B;
            font-size: 1rem;
            margin-bottom: 1.8rem;
        }

        .section-title {
            color: #173B57;
            font-size: 1.25rem;
            font-weight: 700;
            margin-top: 1rem;
            margin-bottom: 0.8rem;
        }

        .metric-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 1.2rem;
            min-height: 110px;
        }

        .metric-label {
            color: #64748B;
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            color: #173B57;
            font-size: 1.35rem;
            font-weight: 700;
            overflow-wrap: anywhere;
        }

        .item-card {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.7rem;
        }

        .item-name {
            color: #173B57;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.4rem;
        }

        .item-details {
            color: #64748B;
            font-size: 0.9rem;
        }

        .total-card {
            background-color: #E7EFF5;
            border-radius: 10px;
            padding: 1rem;
            text-align: right;
            margin-top: 0.8rem;
        }

        .total-label {
            color: #475569;
            font-size: 0.9rem;
        }

        .total-value {
            color: #173B57;
            font-size: 1.5rem;
            font-weight: 700;
        }

        div.stButton > button {
            background-color: #173B57;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 0.55rem 1.2rem;
            font-weight: 600;
        }

        div.stButton > button:hover {
            background-color: #245777;
            color: #FFFFFF;
        }

        div[data-testid="stFormSubmitButton"] button {
            background-color: #173B57;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            font-weight: 600;
        }

        div[data-testid="stFormSubmitButton"] button:hover {
            background-color: #245777;
            color: #FFFFFF;
        }

        div[data-testid="stTextArea"] textarea,
        div[data-testid="stTextInput"] input {
            border-radius: 8px;
        }

        [data-testid="stExpander"] {
            background-color: #FFFFFF;
            border-radius: 10px;
            border: 1px solid #E2E8F0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def go_to_analysis():
    """Navega para a página de análise."""
    st.session_state["navigation"] = "Analisar reclamação"


def format_brl(value) -> str:
    """Formata um valor numérico para o padrão monetário brasileiro."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    formatted = f"{number:,.2f}"
    formatted = (
        formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"R$ {formatted}"


def format_status(status) -> str:
    """Converte os status mais comuns para português."""
    if not status:
        return "Não informado"

    translations = {
        "delivered": "Entregue",
        "pending": "Pendente",
        "processing": "Em processamento",
        "cancelled": "Cancelado",
        "canceled": "Cancelado",
        "shipped": "Enviado",
        "in_transit": "Em trânsito",
        "in transit": "Em trânsito",
        "returned": "Devolvido",
        "refunded": "Reembolsado",
    }

    normalized_status = str(status).strip().lower()

    return translations.get(
        normalized_status,
        str(status).replace("_", " ").capitalize(),
    )


def clean_ai_message(message) -> str:
    """Corrige problemas comuns de formatação monetária."""
    if not isinstance(message, str):
        return str(message) if message is not None else ""

    return re.sub(r"R\\?`\s*", "R$ ", message)


def display_value(value) -> str:
    """Converte valores estruturados em texto legível."""
    if value is None:
        return "Não informado"

    if isinstance(value, bool):
        return "Sim" if value else "Não"

    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return clean_ai_message(str(value))


def render_list(title: str, values):
    """Exibe uma lista de informações sem mostrar a estrutura Python."""
    st.markdown(f"#### {title}")

    if values is None or values == [] or values == "":
        st.write("Nenhuma informação registrada.")
        return

    if not isinstance(values, list):
        values = [values]

    for value in values:
        if isinstance(value, dict):
            # Tenta apresentar cada campo do dicionário de forma legível.
            for key, item_value in value.items():
                readable_key = str(key).replace("_", " ").capitalize()
                st.markdown(
                    f"- **{readable_key}:** {display_value(item_value)}"
                )
        else:
            st.markdown(f"- {display_value(value)}")


def metric_card(label, value):
    """Exibe um cartão de informação."""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{safe_label}</div>
            <div class="metric-value">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_error_detail(response) -> str:
    """Obtém uma mensagem de erro legível a partir da resposta HTTP."""
    try:
        data = response.json()
    except ValueError:
        return ""

    if not isinstance(data, dict):
        return ""

    detail = data.get("detail", "")

    if isinstance(detail, list):
        messages = []

        for item in detail:
            if isinstance(item, dict):
                messages.append(str(item.get("msg", item)))
            else:
                messages.append(str(item))

        return "; ".join(messages)

    if isinstance(detail, str):
        return detail

    return ""


# ============================================================
# COMUNICAÇÃO COM A API
# ============================================================

def analyze_complaint(order_id: str, customer_message: str) -> dict:
    """Envia os dados para a API e retorna o resultado da análise."""

    endpoint = f"{API_URL}/orders/analyze"

    payload = {
        "order_id": order_id,
        "customer_message": customer_message,
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=60,
        )

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Não foi possível conectar à API. "
            "Verifique se o backend está em execução "
            "e se a URL configurada está correta."
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            "A requisição excedeu o tempo limite de 60 segundos. "
            "Verifique os logs do backend antes de tentar novamente."
        ) from exc

    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "Ocorreu um erro de comunicação com a API. "
            "Verifique a conexão e os logs do backend."
        ) from exc

    if response.status_code == 404:
        raise RuntimeError(
            "Pedido não encontrado. Verifique o identificador informado."
        )

    if response.status_code == 422:
        detail = get_error_detail(response)
        raise RuntimeError(
            f"Os dados enviados não foram aceitos pela API. {detail}"
            if detail
            else "Os dados enviados não foram aceitos pela API."
        )

    if response.status_code == 503:
        detail = get_error_detail(response)
        normalized_detail = detail.lower()

        if any(
            term in normalized_detail
            for term in (
                "limite de requisições",
                "limite de requisicoes",
                "quota",
                "resource_exhausted",
                "rate limit",
                "429",
            )
        ):
            raise RuntimeError(
                "O serviço de IA atingiu o limite de requisições. "
                "Aguarde a renovação da cota antes de tentar novamente."
            )

        raise RuntimeError(
            detail
            or "O serviço de IA está temporariamente indisponível."
        )

    if response.status_code >= 500:
        raise RuntimeError(
            f"O servidor retornou o erro HTTP {response.status_code}. "
            "Verifique os logs do backend."
        )

    if not response.ok:
        detail = get_error_detail(response)
        raise RuntimeError(
            detail or f"A API retornou o erro HTTP {response.status_code}."
        )

    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            "A API respondeu com um conteúdo que não é um JSON válido."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "A API retornou uma resposta em formato inesperado."
        )

    return result


# ============================================================
# ESTADO DA APLICAÇÃO
# ============================================================

if "navigation" not in st.session_state:
    previous_page = st.session_state.get("page", "Visão geral")

    if previous_page not in ["Visão geral", "Analisar reclamação"]:
        previous_page = "Visão geral"

    st.session_state["navigation"] = previous_page

if "last_analysis" not in st.session_state:
    st.session_state["last_analysis"] = None


# ============================================================
# BARRA LATERAL
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 0.8rem 0 1.5rem 0;">
            <div style="font-size: 1.8rem; font-weight: 700;">
                📦 OrderMind AI
            </div>
            <div style="font-size: 0.85rem; opacity: 0.8;">
                Inteligência para pedidos e reclamações
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    selected_page = st.radio(
        "Navegação",
        options=["Visão geral", "Analisar reclamação"],
        key="navigation",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown(
        """
        <div style="font-size: 0.8rem; opacity: 0.75;">
            OrderMind AI<br>
            Análise inteligente de pedidos
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PÁGINA: VISÃO GERAL
# ============================================================

if selected_page == "Visão geral":

    st.markdown(
        '<div class="main-title">OrderMind AI</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtitle">
            Analise pedidos e reclamações de clientes com o auxílio
            de inteligência artificial.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        O OrderMind AI ajuda a consultar informações de pedidos e
        analisar reclamações de clientes para facilitar o atendimento.
        """
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card("Consulta de pedidos", "Informações do pedido")

    with col2:
        metric_card("Análise de reclamações", "Interpretação com IA")

    with col3:
        metric_card("Apoio ao atendimento", "Informações centralizadas")

    st.markdown(
        '<div class="section-title">Como começar</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        1. Acesse **Analisar reclamação** no menu lateral.
        2. Informe o identificador do pedido.
        3. Escreva a reclamação apresentada pelo cliente.
        4. Clique em **Analisar reclamação** para visualizar o resultado.
        """
    )

    st.button(
        "Analisar uma reclamação",
        key="start_analysis",
        on_click=go_to_analysis,
    )


# ============================================================
# PÁGINA: ANALISAR RECLAMAÇÃO
# ============================================================

elif selected_page == "Analisar reclamação":

    st.markdown(
        '<div class="main-title">Analisar reclamação</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="subtitle">
            Informe os dados do pedido e a mensagem do cliente
            para realizar a análise.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("complaint_form"):

        order_id = st.text_input(
            "Identificador do pedido",
            placeholder="Ex.: PED-1001",
            help="Informe o identificador do pedido que deseja consultar.",
        )

        customer_message = st.text_area(
            "Reclamação do cliente",
            placeholder="Descreva a reclamação apresentada pelo cliente...",
            height=150,
            help="Escreva a mensagem que será analisada.",
        )

        submitted = st.form_submit_button(
            "Analisar reclamação",
            use_container_width=True,
        )

    if submitted:
        st.session_state["last_analysis"] = None

        if not order_id.strip():
            st.warning(
                "Informe o identificador do pedido antes de continuar."
            )

        elif not customer_message.strip():
            st.warning(
                "Informe a reclamação do cliente antes de continuar."
            )

        else:
            with st.spinner(
                "Consultando o pedido e analisando a reclamação..."
            ):
                try:
                    result = analyze_complaint(
                        order_id=order_id.strip(),
                        customer_message=customer_message.strip(),
                    )
                    st.session_state["last_analysis"] = result

                except RuntimeError as exc:
                    st.error(str(exc))

                except Exception as exc:
                    st.error(
                        "Ocorreu um erro inesperado durante a análise. "
                        "Verifique os logs do backend."
                    )
                    print(
                        f"Erro inesperado na análise: "
                        f"{type(exc).__name__}: {exc}"
                    )

    # ========================================================
    # EXIBIÇÃO DO RESULTADO
    # ========================================================

    result = st.session_state.get("last_analysis")

    if result:

        st.markdown("---")

        st.markdown(
            '<div class="section-title">Informações do pedido</div>',
            unsafe_allow_html=True,
        )

        order_data = result.get("order", result)

        if not isinstance(order_data, dict):
            order_data = result

        displayed_order_id = (
            order_data.get("order_id")
            or order_data.get("id")
            or result.get("order_id")
            or "Não informado"
        )

        status = order_data.get("status") or result.get("status")

        customer_id = (
            order_data.get("customer_id")
            or result.get("customer_id")
            or "Não informado"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            metric_card("Pedido", displayed_order_id)

        with col2:
            metric_card("Status", format_status(status))

        with col3:
            metric_card("Cliente", customer_id)

        # ====================================================
        # ITENS DO PEDIDO
        # ====================================================

        items = (
            order_data.get("items")
            or order_data.get("order_items")
            or result.get("items")
            or result.get("order_items")
            or []
        )

        st.markdown(
            '<div class="section-title">Itens do pedido</div>',
            unsafe_allow_html=True,
        )

        if isinstance(items, list) and items:

            for item in items:
                if not isinstance(item, dict):
                    st.write(display_value(item))
                    continue

                item_name = (
                    item.get("name")
                    or item.get("product_name")
                    or item.get("product")
                    or "Item sem nome"
                )

                quantity = item.get("quantity") or item.get("amount") or 1

                unit_price = (
                    item.get("unit_price")
                    if item.get("unit_price") is not None
                    else item.get("price")
                )

                total_price = (
                    item.get("total_price")
                    if item.get("total_price") is not None
                    else item.get("subtotal")
                )

                if total_price is None:
                    try:
                        total_price = float(unit_price) * float(quantity)
                    except (TypeError, ValueError):
                        total_price = None

                safe_item_name = html.escape(str(item_name))
                safe_quantity = html.escape(str(quantity))

                formatted_unit_price = format_brl(unit_price)
                formatted_total_price = format_brl(total_price)

                st.markdown(
                    f"""
                    <div class="item-card">
                        <div class="item-name">
                            {safe_item_name}
                        </div>
                        <div class="item-details">
                            Quantidade: {safe_quantity}
                            &nbsp;|&nbsp;
                            Preço unitário: {formatted_unit_price}
                            &nbsp;|&nbsp;
                            Subtotal: {formatted_total_price}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        else:
            st.info(
                "Não foram encontrados itens para exibir neste pedido."
            )

        # ====================================================
        # VALOR TOTAL
        # ====================================================

        total = (
            order_data.get("total")
            if order_data.get("total") is not None
            else order_data.get("total_amount")
        )

        if total is None:
            total = (
                result.get("total")
                if result.get("total") is not None
                else result.get("total_amount")
            )

        if total is not None:
            st.markdown(
                f"""
                <div class="total-card">
                    <div class="total-label">
                        Valor total do pedido
                    </div>
                    <div class="total-value">
                        {format_brl(total)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ====================================================
        # ANÁLISE DA RECLAMAÇÃO
        # ====================================================

        st.markdown(
            '<div class="section-title">Análise da reclamação</div>',
            unsafe_allow_html=True,
        )

        analysis_message = result.get("message")
        analysis_data = result.get("analysis")

        # O campo message é uma string segundo AnalysisResponse.
        if isinstance(analysis_message, str) and analysis_message.strip():
            st.markdown(clean_ai_message(analysis_message))
        else:
            st.info("A API não retornou um resumo textual da análise.")

        # Exibe os campos estruturados de ComplaintAnalysis.
        if isinstance(analysis_data, dict):

            render_list(
                "Fatos confirmados",
                analysis_data.get("confirmed_facts"),
            )

            render_list(
                "Evidências",
                analysis_data.get("evidence"),
            )

            st.markdown("#### Avaliação da reclamação")
            complaint_assessment = analysis_data.get("complaint_assessment")

            if complaint_assessment:
                st.write(display_value(complaint_assessment))
            elif not analysis_message:
                st.write("Nenhuma avaliação foi informada.")

            st.markdown("#### Próxima ação recomendada")
            recommended_next_step = analysis_data.get("recommended_next_step")

            if recommended_next_step:
                st.write(display_value(recommended_next_step))
            else:
                st.write("Nenhuma ação recomendada informada.")

            missing_information = analysis_data.get("missing_information")

            if missing_information:
                render_list(
                    "Informações que faltam",
                    missing_information,
                )

            st.markdown("#### Revisão humana")
            requires_human_review = analysis_data.get(
                "requires_human_review"
            )

            if requires_human_review is True:
                st.warning(
                    "Este caso precisa ser revisado por uma pessoa."
                )
            elif requires_human_review is False:
                st.success(
                    "A análise não sinalizou necessidade de revisão humana."
                )
            else:
                st.info(
                    "A necessidade de revisão humana não foi informada."
                )

        elif analysis_data is not None:
            st.warning(
                "A API retornou os detalhes da análise em um formato "
                "inesperado."
            )
        else:
            st.info(
                "A API não retornou os detalhes estruturados da análise."
            )

        # ====================================================
        # MENSAGEM ORIGINAL DO CLIENTE
        # ====================================================

        original_message = (
            result.get("customer_message")
            or result.get("original_message")
            or result.get("complaint")
            or "Mensagem original não disponível."
        )

        with st.expander("Ver mensagem original do cliente"):
            st.write(original_message)
