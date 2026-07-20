from datetime import date

from django.db import migrations


FAQ_RECORDS = [
    {
        "faq_id": "FAQ-001",
        "category": "Shipping",
        "question": "How long does standard shipping take?",
        "approved_answer": (
            "In-stock orders normally process in 1-2 business days, followed by "
            "an estimated 3-7 business days in transit within the contiguous "
            "United States. Carrier estimates are not guarantees."
        ),
        "keywords": "how, long, standard, shipping, transit",
    },
    {
        "faq_id": "FAQ-002",
        "category": "Shipping",
        "question": "When is standard shipping free?",
        "approved_answer": (
            "Eligible merchandise subtotals of $75 or more receive free standard "
            "shipping before tax and after discounts. Oversized, bulk, Alaska, "
            "Hawaii, territories, and international orders are excluded."
        ),
        "keywords": "free shipping, threshold, standard shipping",
    },
    {
        "faq_id": "FAQ-003",
        "category": "Shipping",
        "question": "Can I change my delivery address?",
        "approved_answer": (
            "The assistant cannot change an address. If fulfillment has not "
            "started, a support specialist may review the request, but a change "
            "is not guaranteed."
        ),
        "keywords": "change address, delivery address, fulfillment",
    },
    {
        "faq_id": "FAQ-004",
        "category": "Shipping",
        "question": "My tracking has not updated. Is my package lost?",
        "approved_answer": (
            "A first carrier scan can take up to 24 hours. The assistant should "
            "not declare a package lost; it can create a support request if the "
            "delay continues or the customer is concerned."
        ),
        "keywords": "tracking, carrier scan, package delay, lost package",
    },
    {
        "faq_id": "FAQ-005",
        "category": "Returns",
        "question": "What is the return window?",
        "approved_answer": (
            "Most unused, unwashed, non-personalized items in original condition "
            "may be requested for return within 30 calendar days of recorded "
            "delivery, subject to review."
        ),
        "keywords": "return window, 30 days, return eligibility",
    },
    {
        "faq_id": "FAQ-006",
        "category": "Returns",
        "question": "Are final-sale items returnable?",
        "approved_answer": (
            "Final-sale items are generally not eligible for return except where "
            "required by applicable law or separately approved by a human."
        ),
        "keywords": "final sale, return exclusion, policy exception",
    },
    {
        "faq_id": "FAQ-007",
        "category": "Returns",
        "question": "Who pays return shipping?",
        "approved_answer": (
            "Customers normally pay return shipping for preference-based returns. "
            "Wrong-item or verified-damage claims require human review before a "
            "resolution is approved."
        ),
        "keywords": "return shipping, return cost, wrong item, damage",
    },
    {
        "faq_id": "FAQ-008",
        "category": "Returns",
        "question": "How long do refunds take?",
        "approved_answer": (
            "After an approved return is received and inspected, a refund is "
            "normally initiated within 5-10 business days. The financial "
            "institution may need additional time."
        ),
        "keywords": "refund timing, return inspection, 5-10 business days",
    },
    {
        "faq_id": "FAQ-009",
        "category": "Orders",
        "question": "Can the bot cancel my order?",
        "approved_answer": (
            "No. The assistant can create a high-priority cancellation request, "
            "but cancellation is not complete until an authorized system or "
            "person confirms it."
        ),
        "keywords": "cancel order, cancellation request, order change",
    },
    {
        "faq_id": "FAQ-010",
        "category": "Orders",
        "question": "Can I add an item to my order?",
        "approved_answer": (
            "The assistant cannot edit an order. It can create a handoff for "
            "review, but fulfillment status may prevent changes."
        ),
        "keywords": "add item, edit order, fulfillment, order change",
    },
    {
        "faq_id": "FAQ-011",
        "category": "Damage",
        "question": "What should I do if an item arrived damaged?",
        "approved_answer": (
            "Report it as soon as practical, preferably within 7 days. Provide "
            "the order ID, affected item, and a description; a human will review "
            "photos and possible resolutions."
        ),
        "keywords": "damaged item, wrong item, photos, damage report",
    },
    {
        "faq_id": "FAQ-012",
        "category": "Safety",
        "question": "What if a product caused an injury or overheated?",
        "approved_answer": (
            "Stop using the product and request urgent human support. The "
            "assistant must not diagnose, assign fault, or promise a resolution."
        ),
        "keywords": "injury, overheating, safety, urgent support",
    },
    {
        "faq_id": "FAQ-013",
        "category": "Payments",
        "question": "Can I give the chatbot my card number?",
        "approved_answer": (
            "No. Never share full payment credentials, passwords, gift-card "
            "codes, or government IDs in chat."
        ),
        "keywords": "card number, payment credentials, password, sensitive data",
    },
    {
        "faq_id": "FAQ-014",
        "category": "Discounts",
        "question": "Can the bot create a discount code?",
        "approved_answer": (
            "No. It can explain an approved active code but cannot create a code, "
            "override restrictions, or promise a manual discount."
        ),
        "keywords": "discount code, promotion, coupon, override",
    },
    {
        "faq_id": "FAQ-015",
        "category": "Products",
        "question": "Are natural material variations defects?",
        "approved_answer": (
            "Natural wood, bamboo, cotton, linen, stone, and woven fibers can "
            "show normal variation. Specific damage or defects require human review."
        ),
        "keywords": "natural variation, materials, wood, bamboo, defect",
    },
    {
        "faq_id": "FAQ-016",
        "category": "Products",
        "question": "How should I clean bamboo products?",
        "approved_answer": (
            "Follow the product record first. Otherwise, wipe with a soft damp "
            "cloth, avoid abrasive cleaners, and do not soak bamboo."
        ),
        "keywords": "bamboo care, clean bamboo, care instructions",
    },
    {
        "faq_id": "FAQ-017",
        "category": "Privacy",
        "question": "Can I ask to delete my personal data?",
        "approved_answer": (
            "Yes, but the assistant cannot complete or verify the request. It "
            "must create a privacy handoff to the authorized human owner."
        ),
        "keywords": "delete data, privacy request, personal data",
    },
    {
        "faq_id": "FAQ-018",
        "category": "Support",
        "question": "How quickly will a person reply?",
        "approved_answer": (
            "During business hours, human requests are normally reviewed within "
            "one business day. This is a target, not a guarantee."
        ),
        "keywords": "human reply, response time, business day, support",
    },
    {
        "faq_id": "FAQ-019",
        "category": "Bulk",
        "question": "Do you offer bulk pricing?",
        "approved_answer": (
            "Bulk inquiries are reviewed case by case. The assistant can capture "
            "quantity, desired date, ZIP code, and contact information for a "
            "written quote."
        ),
        "keywords": "bulk pricing, quantity, quote, wholesale",
    },
    {
        "faq_id": "FAQ-020",
        "category": "Trade",
        "question": "Can I join the trade program?",
        "approved_answer": (
            "The mock trade program is reviewed case by case. The assistant can "
            "capture interest but cannot promise approval, terms, or discounts."
        ),
        "keywords": "trade program, application, approval, trade discount",
    },
]


def load_harbor_pine_faqs(apps, schema_editor):
    faq_model = apps.get_model("knowledge", "FAQ")

    common_values = {
        "is_enabled": True,
        "effective_date": date(2026, 7, 1),
        "review_date": date(2026, 10, 1),
        "owner": "Support Operations Manager",
    }

    for record in FAQ_RECORDS:
        faq_id = record["faq_id"]
        defaults = {
            **record,
            **common_values,
        }
        defaults.pop("faq_id")

        faq_model.objects.update_or_create(
            faq_id=faq_id,
            defaults=defaults,
        )


def remove_harbor_pine_faqs(apps, schema_editor):
    faq_model = apps.get_model("knowledge", "FAQ")
    faq_ids = [record["faq_id"] for record in FAQ_RECORDS]
    faq_model.objects.filter(faq_id__in=faq_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            load_harbor_pine_faqs,
            remove_harbor_pine_faqs,
        ),
    ]
