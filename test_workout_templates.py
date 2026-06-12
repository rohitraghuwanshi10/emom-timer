import unittest
import storage
import json
import os

class TestWorkoutTemplates(unittest.TestCase):
    def setUp(self):
        # Add a test profile to work with
        self.profile_name = "TestTemplateProfile"
        storage.add_profile(self.profile_name)

    def test_save_get_delete_template(self):
        # 1. Verify initially templates is empty
        templates = storage.get_templates(self.profile_name)
        self.assertEqual(templates, {})

        # 2. Save a template
        storage.save_template(
            self.profile_name,
            "Heavy Swings",
            rounds=10,
            work_time=60,
            rest_time=30,
            notes="10 rounds of double kettlebell swings"
        )

        # 3. Retrieve and verify
        templates = storage.get_templates(self.profile_name)
        self.assertIn("Heavy Swings", templates)
        self.assertEqual(templates["Heavy Swings"]["rounds"], 10)
        self.assertEqual(templates["Heavy Swings"]["work_time"], 60)
        self.assertEqual(templates["Heavy Swings"]["rest_time"], 30)
        self.assertEqual(templates["Heavy Swings"]["notes"], "10 rounds of double kettlebell swings")

        # 4. Save another template to verify multiple
        storage.save_template(
            self.profile_name,
            "ABC - Double 18KG",
            rounds=5,
            work_time=45,
            rest_time=15,
            notes="ABC sequence"
        )

        templates = storage.get_templates(self.profile_name)
        self.assertEqual(len(templates), 2)
        self.assertIn("ABC - Double 18KG", templates)

        # 5. Delete one template
        storage.delete_template(self.profile_name, "Heavy Swings")
        templates = storage.get_templates(self.profile_name)
        self.assertEqual(len(templates), 1)
        self.assertNotIn("Heavy Swings", templates)
        self.assertIn("ABC - Double 18KG", templates)

        # 6. Delete last template
        storage.delete_template(self.profile_name, "ABC - Double 18KG")
        templates = storage.get_templates(self.profile_name)
        self.assertEqual(templates, {})

if __name__ == '__main__':
    unittest.main()
