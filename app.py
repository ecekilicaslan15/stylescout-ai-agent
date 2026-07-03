import streamlit as st

from memory.memory_store import load_memory, update_memory_from_input
from orchestrator.fashion_orchestrator import run_fashion_agent
from wardrobe.wardrobe_manager import load_wardrobe, update_wardrobe_from_input


st.set_page_config(
    page_title="StyleScout",
    page_icon="👗",
    layout="wide",
)

CATEGORY_VISUALS = {
    "tops": "👚",
    "top": "👚",
    "bottoms": "👖",
    "bottom": "👖",
    "shoes": "👠",
    "outerwear": "🧥",
    "accessories": "👜",
    "accessory": "👜",
}

WARDROBE_SECTIONS = [
    ("tops", "Tops"),
    ("bottoms", "Bottoms"),
    ("shoes", "Shoes"),
    ("outerwear", "Outerwear"),
    ("accessories", "Accessories"),
]


def format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "Not set yet"


def render_wardrobe_section(wardrobe: dict) -> None:
    wardrobe_html = (
        '<div class="scrapbook-card">'
        '<p class="section-label">Your Wardrobe</p>'
        '<p class="card-title">Saved pieces</p>'
        '<p class="card-copy">Clothes you have added to your personal wardrobe.</p>'
        '<div class="plan-grid">'
    )

    for category_key, category_label in WARDROBE_SECTIONS:
        items = wardrobe.get(category_key, [])
        wardrobe_html += (
            f'<div class="plan-item">'
            f'<div class="plan-key">{category_label}</div>'
            f'<div class="memory-row">'
        )

        if items:
            for item in items:
                wardrobe_html += f'<span class="memory-chip">{item["name"]}</span>'
        else:
            wardrobe_html += '<span class="memory-chip empty">Empty</span>'

        wardrobe_html += "</div></div>"

    wardrobe_html += "</div></div>"
    st.markdown(wardrobe_html, unsafe_allow_html=True)


def render_section_label(title: str) -> None:
    st.markdown(
        f'<p class="section-label">{title}</p>',
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(180deg, #faf7f2 0%, #fffdf9 100%);
        }

        .block-container {
            max-width: 920px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hero-scrapbook {
            background: #fffdf9;
            border: 1px solid #e7e0d5;
            border-radius: 28px;
            padding: 2rem 2rem 1.75rem;
            box-shadow: 0 18px 40px rgba(46, 196, 182, 0.08);
            position: relative;
            overflow: hidden;
            margin-bottom: 1.25rem;
        }

        .hero-scrapbook::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(90deg, #2ec4b6 0%, #7fded6 55%, #f4a9c8 100%);
        }

        .hero-kicker {
            display: inline-block;
            font-size: 0.72rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: #2ec4b6;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .hero-title {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 2.6rem;
            line-height: 1.05;
            color: #24343a;
            margin: 0 0 0.65rem 0;
            font-weight: 700;
        }

        .hero-subtitle {
            color: #667781;
            font-size: 1.05rem;
            max-width: 620px;
            margin: 0 0 1rem 0;
            line-height: 1.6;
        }

        .hero-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        .hero-tag {
            display: inline-block;
            padding: 0.35rem 0.8rem;
            border-radius: 999px;
            background: #eefcf9;
            color: #14867c;
            border: 1px solid #c9f0ea;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .hero-tag.pink {
            background: #fff1f7;
            color: #b45f84;
            border-color: #f8d7e7;
        }

        .scrapbook-card {
            background: #fffdf9;
            border: 1px solid #e7e0d5;
            border-radius: 22px;
            padding: 1.25rem 1.35rem 1.1rem;
            box-shadow: 0 10px 24px rgba(36, 52, 58, 0.05);
            margin-bottom: 1rem;
        }

        .section-label {
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #2ec4b6;
            font-weight: 700;
            margin: 0 0 0.55rem 0;
        }

        .card-title {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.45rem;
            color: #24343a;
            margin: 0 0 0.35rem 0;
        }

        .card-copy {
            color: #667781;
            font-size: 0.95rem;
            line-height: 1.55;
            margin: 0 0 0.75rem 0;
        }

        .memory-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.35rem;
        }

        .memory-chip {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            background: #eefcf9;
            color: #14867c;
            border: 1px solid #c9f0ea;
            font-size: 0.84rem;
        }

        .memory-chip.pink {
            background: #fff1f7;
            color: #b45f84;
            border-color: #f8d7e7;
        }

        .memory-chip.empty {
            background: #f5f1ea;
            color: #8a8178;
            border-color: #e7e0d5;
        }

        .plan-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem 1rem;
        }

        .plan-item {
            background: #faf7f2;
            border: 1px dashed #ddd4c7;
            border-radius: 16px;
            padding: 0.8rem 0.9rem;
        }

        .plan-key {
            font-size: 0.72rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #2ec4b6;
            margin-bottom: 0.25rem;
            font-weight: 700;
        }

        .plan-value {
            color: #24343a;
            font-size: 0.98rem;
            font-weight: 600;
            text-transform: capitalize;
        }

        .item-card {
            background: #fffdf9;
            border: 1px solid #e7e0d5;
            border-radius: 20px;
            padding: 1rem;
            box-shadow: 0 8px 20px rgba(36, 52, 58, 0.05);
            height: 100%;
        }

        .item-visual {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 118px;
            border-radius: 16px;
            background: linear-gradient(135deg, #eefcf9 0%, #fff1f7 100%);
            border: 1px solid #dcefe9;
            font-size: 2.8rem;
            margin-bottom: 0.85rem;
        }

        .item-name {
            font-family: Georgia, "Times New Roman", serif;
            font-size: 1.08rem;
            color: #24343a;
            margin: 0 0 0.25rem 0;
            font-weight: 700;
        }

        .item-meta {
            color: #667781;
            font-size: 0.88rem;
            margin: 0;
            text-transform: capitalize;
        }

        .reason-card {
            background: linear-gradient(135deg, #eefcf9 0%, #fffdf9 100%);
            border: 1px solid #c9f0ea;
            border-left: 4px solid #2ec4b6;
            border-radius: 20px;
            padding: 1.1rem 1.2rem;
        }

        .reason-text {
            color: #42545b;
            font-size: 0.98rem;
            line-height: 1.65;
            margin: 0;
        }

        .status-banner {
            background: #eefcf9;
            border: 1px solid #c9f0ea;
            color: #14867c;
            border-radius: 16px;
            padding: 0.85rem 1rem;
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .empty-state {
            background: #faf7f2;
            border: 1px dashed #ddd4c7;
            border-radius: 18px;
            padding: 1rem 1.1rem;
            color: #667781;
            font-size: 0.95rem;
            line-height: 1.55;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e7e0d5 !important;
            border-radius: 22px !important;
            background: #fffdf9;
            box-shadow: 0 10px 24px rgba(36, 52, 58, 0.05);
        }

        div[data-testid="stTextArea"] textarea {
            border-radius: 16px !important;
            border-color: #ddd4c7 !important;
            background: #fffdf9 !important;
        }

        div[data-testid="stButton"] button[kind="primary"] {
            background: #2ec4b6 !important;
            border: 1px solid #2ec4b6 !important;
            color: white !important;
            border-radius: 999px !important;
            font-weight: 700 !important;
        }

        div[data-testid="stButton"] button[kind="primary"]:hover {
            background: #24a89c !important;
            border-color: #24a89c !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-scrapbook">
        <div class="hero-kicker">Editorial Moodboard</div>
        <h1 class="hero-title">StyleScout</h1>
        <p class="hero-subtitle">
            A playful scrapbook-style fashion dashboard for planning looks,
            remembering your taste, and building outfits with calm confidence.
        </p>
        <div class="hero-tags">
            <span class="hero-tag">Turquoise Edit</span>
            <span class="hero-tag pink">Soft Pink Notes</span>
            <span class="hero-tag">AI Styling Desk</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container(border=True):
    render_section_label("Your Brief")
    st.markdown(
        '<p class="card-title">Describe your look</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="card-copy">Share the occasion, mood, city, colors, or anything you want me to remember.</p>',
        unsafe_allow_html=True,
    )

    user_input = st.text_area(
        "What kind of outfit do you need?",
        placeholder="Example: I need an elegant office outfit in Istanbul. I like black and beige.",
        height=120,
        label_visibility="collapsed",
    )

    generate_clicked = st.button(
        "Generate Outfit",
        type="primary",
        use_container_width=True,
    )

if generate_clicked:
    if not user_input.strip():
        st.warning("Please describe what kind of outfit you need.")
    else:
        update_memory_from_input(user_input)
        wardrobe_update = update_wardrobe_from_input(user_input)
        result = run_fashion_agent(user_input)

        plan = result["plan"]
        outfit = result["outfit"]
        memory = load_memory()
        wardrobe = load_wardrobe()
        message = result.get("message", "")

        status_messages = []

        if wardrobe_update:
            item = wardrobe_update["item"]
            if wardrobe_update["added"]:
                status_messages.append(
                    f'Saved <strong>{item["name"]}</strong> to your wardrobe ({item["category"]}).'
                )
            else:
                status_messages.append(
                    f'<strong>{item["name"]}</strong> is already in your wardrobe.'
                )

        if message:
            status_messages.append(message)

        if status_messages:
            st.markdown(
                f'<div class="status-banner">{" ".join(status_messages)}</div>',
                unsafe_allow_html=True,
            )

        favorite_colors = memory.get("favorite_colors", [])
        preferred_styles = memory.get("preferred_styles", [])
        disliked_items = memory.get("disliked_items", [])

        st.markdown('<div class="scrapbook-card">', unsafe_allow_html=True)
        render_section_label("Style Memory")
        st.markdown(
            '<p class="card-title">Your saved taste</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="card-copy">A quick snapshot of what StyleScout remembers about your style profile.</p>',
            unsafe_allow_html=True,
        )

        memory_html = """
        <div class="plan-grid">
            <div class="plan-item">
                <div class="plan-key">Favorite Colors</div>
                <div class="memory-row">
        """
        if favorite_colors:
            for color in favorite_colors:
                memory_html += f'<span class="memory-chip">{color}</span>'
        else:
            memory_html += '<span class="memory-chip empty">Not set yet</span>'

        memory_html += """
                </div>
            </div>
            <div class="plan-item">
                <div class="plan-key">Preferred Styles</div>
                <div class="memory-row">
        """
        if preferred_styles:
            for style in preferred_styles:
                memory_html += f'<span class="memory-chip">{style}</span>'
        else:
            memory_html += '<span class="memory-chip empty">Not set yet</span>'

        memory_html += """
                </div>
            </div>
            <div class="plan-item" style="grid-column: 1 / -1;">
                <div class="plan-key">Disliked Items</div>
                <div class="memory-row">
        """
        if disliked_items:
            for item in disliked_items:
                memory_html += f'<span class="memory-chip pink">{item}</span>'
        else:
            memory_html += '<span class="memory-chip empty">Not set yet</span>'

        memory_html += """
                </div>
            </div>
        </div>
        """
        st.markdown(memory_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        render_wardrobe_section(wardrobe)

        st.markdown('<div class="scrapbook-card">', unsafe_allow_html=True)
        render_section_label("Detected Plan")
        st.markdown(
            '<p class="card-title">What I understood</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="plan-grid">
                <div class="plan-item">
                    <div class="plan-key">Intent</div>
                    <div class="plan-value">{plan.intent.replace("_", " ")}</div>
                </div>
                <div class="plan-item">
                    <div class="plan-key">Event</div>
                    <div class="plan-value">{plan.event}</div>
                </div>
                <div class="plan-item">
                    <div class="plan-key">Style</div>
                    <div class="plan-value">{plan.style}</div>
                </div>
                <div class="plan-item">
                    <div class="plan-key">Colors</div>
                    <div class="plan-value">{format_list(plan.colors) if plan.colors else "Not specified"}</div>
                </div>
                <div class="plan-item">
                    <div class="plan-key">City</div>
                    <div class="plan-value">{plan.city if plan.city else "Not specified"}</div>
                </div>
                <div class="plan-item">
                    <div class="plan-key">Date</div>
                    <div class="plan-value">{plan.date if plan.date else "Not specified"}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="scrapbook-card">', unsafe_allow_html=True)
        render_section_label("Recommended Outfit")
        st.markdown(
            '<p class="card-title">Your moodboard picks</p>',
            unsafe_allow_html=True,
        )

        if outfit is None:
            st.markdown(
                """
                <div class="empty-state">
                    No outfit was generated for this request. StyleScout may have
                    focused on updating your style memory instead.
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif outfit["items"]:
            st.markdown(
                f'<p class="card-copy">Curated for <strong>{outfit["event"]}</strong> with a '
                f'<strong>{outfit["style"]}</strong> direction.</p>',
                unsafe_allow_html=True,
            )

            columns = st.columns(min(len(outfit["items"]), 3))
            for index, item in enumerate(outfit["items"]):
                visual = CATEGORY_VISUALS.get(item["category"], "✨")
                with columns[index % len(columns)]:
                    st.markdown(
                        f"""
                        <div class="item-card">
                            <div class="item-visual">{visual}</div>
                            <p class="item-name">{item["name"]}</p>
                            <p class="item-meta">{item["category"]} · {item["color"]}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.markdown(
                """
                <div class="empty-state">
                    No outfit items matched this plan yet. Try adding more pieces to
                    your wardrobe or adjusting your request.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if outfit is not None:
            st.markdown(
                f"""
                <div class="reason-card">
                    <p class="section-label">Why This Outfit</p>
                    <p class="card-title" style="font-size:1.2rem; margin-bottom:0.5rem;">
                        Stylist Notes
                    </p>
                    <p class="reason-text">{outfit["reason"]}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
