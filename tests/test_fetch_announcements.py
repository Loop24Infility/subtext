import unittest
from unittest.mock import patch

from ingestion.fetch_announcements import save_announcements_to_database


class SaveAnnouncementsToDatabaseTests(unittest.TestCase):
    @patch("ingestion.fetch_announcements.psycopg2.connect")
    def test_upserts_company_and_uses_duplicate_guard_for_filings(
        self, connect_mock
    ):
        connection = connect_mock.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (17,)
        cursor.rowcount = 1
        announcements = {
            "TCS": [
                {"announcement_id": "123", "subject": "Results"},
                {"announcement_id": "456", "subject": "Meeting"},
            ]
        }

        inserted_count = save_announcements_to_database(
            announcements, "postgresql://test"
        )

        self.assertEqual(inserted_count, 2)
        connect_mock.assert_called_once_with("postgresql://test")
        self.assertEqual(cursor.execute.call_count, 3)
        self.assertIn(
            "ON CONFLICT (nse_symbol)", cursor.execute.call_args_list[0].args[0]
        )
        self.assertIn("WHERE NOT EXISTS", cursor.execute.call_args_list[1].args[0])
        self.assertEqual(cursor.execute.call_args_list[1].args[1][0], 17)
        self.assertEqual(cursor.execute.call_args_list[2].args[1][0], 17)


if __name__ == "__main__":
    unittest.main()
