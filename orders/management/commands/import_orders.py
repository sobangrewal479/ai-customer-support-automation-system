import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from orders.models import MockOrder


EXPECTED_HEADERS = [
    "order_id",
    "billing_zip",
    "customer_name",
    "customer_email",
    "order_date",
    "status",
    "carrier",
    "tracking_reference",
    "eta_window",
    "items",
    "order_total_usd",
    "last_updated",
]


class Command(BaseCommand):
    help = "Import validated Harbor & Pine mock orders from CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=str(
                settings.BASE_DIR / "data" / "orders.csv"
            ),
            help="CSV path. Defaults to data/orders.csv.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            raise CommandError(
                f"CSV file was not found: {csv_path}"
            )

        created_count = 0
        updated_count = 0
        seen_order_ids = set()

        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            if reader.fieldnames != EXPECTED_HEADERS:
                raise CommandError(
                    "The CSV headings do not match the approved "
                    "mock-order data structure."
                )

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                if not any(
                    (value or "").strip()
                    for value in row.values()
                ):
                    continue

                order_id = (
                    row["order_id"] or ""
                ).strip().upper()

                if not order_id:
                    raise CommandError(
                        f"Row {row_number}: order ID is required."
                    )

                if order_id in seen_order_ids:
                    raise CommandError(
                        f"Row {row_number}: duplicate order ID "
                        f"{order_id} exists in the CSV file."
                    )

                seen_order_ids.add(order_id)

                try:
                    order_values = {
                        "billing_zip": (
                            row["billing_zip"] or ""
                        ).strip(),
                        "customer_name": (
                            row["customer_name"] or ""
                        ).strip(),
                        "customer_email": (
                            row["customer_email"] or ""
                        ).strip(),
                        "order_date": date.fromisoformat(
                            row["order_date"].strip()
                        ),
                        "status": (
                            row["status"] or ""
                        ).strip(),
                        "carrier": (
                            row["carrier"] or ""
                        ).strip(),
                        "tracking_reference": (
                            row["tracking_reference"] or ""
                        ).strip(),
                        "eta_window": (
                            row["eta_window"] or ""
                        ).strip(),
                        "items": (
                            row["items"] or ""
                        ).strip(),
                        "order_total_usd": Decimal(
                            row["order_total_usd"].strip()
                        ),
                        "last_updated": date.fromisoformat(
                            row["last_updated"].strip()
                        ),
                    }
                except (ValueError, InvalidOperation) as error:
                    raise CommandError(
                        f"Row {row_number} ({order_id}) contains "
                        f"an invalid date or total: {error}"
                    ) from error

                order = MockOrder.objects.filter(
                    order_id=order_id
                ).first()

                is_new = order is None

                if is_new:
                    order = MockOrder(
                        order_id=order_id
                    )

                for field_name, value in order_values.items():
                    setattr(
                        order,
                        field_name,
                        value,
                    )

                try:
                    order.full_clean()
                except ValidationError as error:
                    raise CommandError(
                        f"Row {row_number} ({order_id}) failed "
                        f"validation: {error.message_dict}"
                    ) from error

                order.save()

                if is_new:
                    created_count += 1
                else:
                    updated_count += 1

        if not seen_order_ids:
            raise CommandError(
                "The CSV file contains no order records."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(seen_order_ids)} orders: "
                f"{created_count} created, "
                f"{updated_count} updated."
            )
        )