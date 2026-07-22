import csv
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from orders.management.commands.import_orders import (
    EXPECTED_HEADERS,
)
from orders.models import MockOrder


class ImportOrdersCommandTests(TestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(
            self.temporary_directory.cleanup
        )

        self.csv_path = (
            Path(self.temporary_directory.name)
            / "orders.csv"
        )

    def valid_row(self, **overrides):
        row = {
            "order_id": "HPL10001",
            "billing_zip": "78701",
            "customer_name": "Jordan Lee",
            "customer_email": "jordan@example.com",
            "order_date": "2026-07-01",
            "status": "shipped",
            "carrier": "UPS",
            "tracking_reference": "1ZTEST10001",
            "eta_window": "July 8-10, 2026",
            "items": "HPL-ORG-001 x 1",
            "order_total_usd": "49.99",
            "last_updated": "2026-07-02",
        }
        row.update(overrides)

        return row

    def write_csv(self, rows, headers=None):
        selected_headers = (
            headers or EXPECTED_HEADERS
        )

        with self.csv_path.open(
            mode="w",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=selected_headers,
            )
            writer.writeheader()

            for row in rows:
                filtered_row = {
                    header: row.get(header, "")
                    for header in selected_headers
                }
                writer.writerow(filtered_row)

        return self.csv_path

    def test_valid_csv_creates_order(self):
        self.write_csv([
            self.valid_row(),
        ])
        output = StringIO()

        call_command(
            "import_orders",
            str(self.csv_path),
            stdout=output,
        )

        order = MockOrder.objects.get(
            order_id="HPL10001"
        )

        self.assertEqual(
            MockOrder.objects.count(),
            1,
        )
        self.assertEqual(
            order.billing_zip,
            "78701",
        )
        self.assertEqual(
            order.order_total_usd,
            Decimal("49.99"),
        )
        self.assertEqual(
            order.status,
            MockOrder.Status.SHIPPED,
        )
        self.assertIn(
            "1 created, 0 updated",
            output.getvalue(),
        )

    def test_existing_order_is_updated_without_duplicate(self):
        self.write_csv([
            self.valid_row(),
        ])

        call_command(
            "import_orders",
            str(self.csv_path),
            stdout=StringIO(),
        )

        updated_row = self.valid_row(
            status="delivered",
            eta_window="Delivered",
            order_total_usd="59.99",
        )

        self.write_csv([
            updated_row,
        ])
        output = StringIO()

        call_command(
            "import_orders",
            str(self.csv_path),
            stdout=output,
        )

        order = MockOrder.objects.get(
            order_id="HPL10001"
        )

        self.assertEqual(
            MockOrder.objects.count(),
            1,
        )
        self.assertEqual(
            order.status,
            MockOrder.Status.DELIVERED,
        )
        self.assertEqual(
            order.eta_window,
            "Delivered",
        )
        self.assertEqual(
            order.order_total_usd,
            Decimal("59.99"),
        )
        self.assertIn(
            "0 created, 1 updated",
            output.getvalue(),
        )

    def test_duplicate_order_id_is_rejected_and_rolled_back(
        self,
    ):
        duplicate_row = self.valid_row(
            customer_name="Different Customer",
        )

        self.write_csv([
            self.valid_row(),
            duplicate_row,
        ])

        with self.assertRaises(CommandError):
            call_command(
                "import_orders",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(
            MockOrder.objects.count(),
            0,
        )

    def test_incorrect_headers_are_rejected(self):
        invalid_headers = EXPECTED_HEADERS[:-1]

        self.write_csv(
            [
                self.valid_row(),
            ],
            headers=invalid_headers,
        )

        with self.assertRaises(CommandError):
            call_command(
                "import_orders",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(
            MockOrder.objects.count(),
            0,
        )

    def test_invalid_tracking_data_is_rolled_back(self):
        invalid_row = self.valid_row(
            status="shipped",
            carrier="",
            tracking_reference="",
        )

        self.write_csv([
            invalid_row,
        ])

        with self.assertRaises(CommandError):
            call_command(
                "import_orders",
                str(self.csv_path),
                stdout=StringIO(),
            )

        self.assertEqual(
            MockOrder.objects.count(),
            0,
        )

    def test_leading_zero_billing_zip_is_preserved(self):
        row = self.valid_row(
            order_id="HPL10002",
            billing_zip="02108",
        )

        self.write_csv([
            row,
        ])

        call_command(
            "import_orders",
            str(self.csv_path),
            stdout=StringIO(),
        )

        order = MockOrder.objects.get(
            order_id="HPL10002"
        )

        self.assertEqual(
            order.billing_zip,
            "02108",
        )