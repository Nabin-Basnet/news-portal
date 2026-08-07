from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from user.models import Role, User
from .models import AdClick, AdImpression, Advertisement


class AdvertisementWorkflowTests(TestCase):
    def setUp(self):
        self.staff_role, _ = Role.objects.get_or_create(role_name="Staff")
        self.editor_role, _ = Role.objects.get_or_create(role_name="Editor")
        self.admin_role, _ = Role.objects.get_or_create(role_name="Admin")
        self.staff = User.objects.create_user(email="staff@example.com", password="password123", role=self.staff_role)
        self.other_staff = User.objects.create_user(email="other-staff@example.com", password="password123", role=self.staff_role)
        self.editor = User.objects.create_user(email="editor@example.com", password="password123", role=self.editor_role)
        self.admin = User.objects.create_user(email="admin@example.com", password="password123", role=self.admin_role)
        self.client = APIClient()

    def advertisement(self, *, title="Campaign", status=Advertisement.Status.DRAFT, creator=None):
        now = timezone.now()
        return Advertisement.objects.create(
            title=title,
            client_name="Client",
            target_url="https://example.com",
            position=Advertisement.Position.SIDEBAR,
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(days=1),
            status=status,
            creator=creator,
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_public_delivery_and_analytics_only_allow_published_ads(self):
        published = self.advertisement(title="Published", status=Advertisement.Status.PUBLISHED)
        draft = self.advertisement(title="Draft", status=Advertisement.Status.DRAFT)
        submitted = self.advertisement(title="Submitted", status=Advertisement.Status.SUBMITTED)
        under_review = self.advertisement(title="Under review", status=Advertisement.Status.UNDER_REVIEW)
        approved = self.advertisement(title="Approved", status=Advertisement.Status.APPROVED)
        rejected = self.advertisement(title="Rejected", status=Advertisement.Status.REJECTED)
        archived = self.advertisement(title="Archived", status=Advertisement.Status.ARCHIVED)

        response = self.client.get("/api/ads/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sidebar"]["id"], published.id)
        delivered_ids = [ad["id"] for ad in response.json().values() if ad]
        for unpublished in (draft, submitted, under_review, approved, rejected, archived):
            self.assertNotIn(unpublished.id, delivered_ids)

        self.assertEqual(self.client.post("/api/ads/impressions/", {"ad_id": published.id}, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/ads/click/", {"ad_id": published.id}, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/ads/impressions/", {"ad_id": draft.id}, format="json").status_code, 404)
        self.assertEqual(self.client.post("/api/ads/click/", {"ad_id": draft.id}, format="json").status_code, 404)
        self.assertEqual(AdImpression.objects.filter(ad=published).count(), 1)
        self.assertEqual(AdClick.objects.filter(ad=published).count(), 1)

    def test_staff_ownership_and_editorial_workflow(self):
        ad = self.advertisement(creator=self.staff)
        other_ad = self.advertisement(title="Other", creator=self.other_staff)

        self.authenticate(self.staff)
        self.assertEqual(self.client.patch(f"/api/ads/{ad.id}/", {"title": "Staff draft edit"}, format="json").status_code, 200)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/submit/").status_code, 200)
        ad.refresh_from_db()
        self.assertEqual(ad.status, Advertisement.Status.SUBMITTED)
        self.assertEqual(self.client.patch(f"/api/ads/{other_ad.id}/", {"title": "No"}, format="json").status_code, 403)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/approve/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/publish/").status_code, 403)

        self.authenticate(self.editor)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/start-review/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/approve/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/publish/").status_code, 200)
        ad.refresh_from_db()
        self.assertEqual(ad.status, Advertisement.Status.PUBLISHED)
        self.assertIsNotNone(ad.published_at)

    def test_staff_can_revise_and_resubmit_own_rejected_advertisement(self):
        ad = self.advertisement(status=Advertisement.Status.REJECTED, creator=self.staff)
        self.authenticate(self.staff)

        self.assertEqual(
            self.client.patch(f"/api/ads/{ad.id}/", {"title": "Revised campaign"}, format="json").status_code,
            200,
        )
        self.assertEqual(self.client.post(f"/api/ads/{ad.id}/submit/").status_code, 200)
        ad.refresh_from_db()
        self.assertEqual(ad.status, Advertisement.Status.SUBMITTED)
        self.assertEqual(ad.title, "Revised campaign")

    def test_staff_create_is_draft_and_admin_can_reject_and_archive(self):
        self.authenticate(self.staff)
        response = self.client.post(
            "/api/ads/",
            {
                "title": "Staff-created campaign",
                "client_name": "Client",
                "image": SimpleUploadedFile("banner.gif", b"GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif"),
                "target_url": "https://example.com",
                "position": Advertisement.Position.SIDEBAR,
                "end_date": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        created = Advertisement.objects.get(title="Staff-created campaign")
        self.assertEqual(created.creator_id, self.staff.id)
        self.assertEqual(created.status, Advertisement.Status.DRAFT)

        rejected = self.advertisement(status=Advertisement.Status.UNDER_REVIEW, creator=self.staff)
        approved = self.advertisement(title="Approved", status=Advertisement.Status.APPROVED, creator=self.staff)
        self.authenticate(self.admin)
        self.assertEqual(self.client.post(f"/api/ads/{rejected.id}/reject/", {"note": "Needs revision"}, format="json").status_code, 200)
        self.assertEqual(self.client.post(f"/api/ads/{approved.id}/publish/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/ads/{approved.id}/archive/").status_code, 200)
        rejected.refresh_from_db()
        approved.refresh_from_db()
        self.assertEqual(rejected.status, Advertisement.Status.REJECTED)
        self.assertEqual(approved.status, Advertisement.Status.ARCHIVED)

    def test_admin_list_has_all_statuses_filters_search_and_pagination(self):
        for workflow_status in Advertisement.Status.values:
            self.advertisement(title=f"Workflow {workflow_status}", status=workflow_status, creator=self.staff)
        for index in range(4):
            self.advertisement(title=f"Pagination {index}", creator=self.staff)

        self.authenticate(self.admin)
        response = self.client.get("/api/ads/admin/ads/", {"page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 11)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertIn("status", response.json()["results"][0])
        self.assertIn("impression_count", response.json()["results"][0])

        filtered = self.client.get("/api/ads/admin/ads/", {"status": Advertisement.Status.ARCHIVED})
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["count"], 1)
        self.assertEqual(filtered.json()["results"][0]["status"], Advertisement.Status.ARCHIVED)

        searched = self.client.get("/api/ads/admin/ads/", {"search": "Workflow approved"})
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(searched.json()["count"], 1)

        self.authenticate(self.staff)
        self.assertEqual(self.client.get("/api/ads/admin/ads/").status_code, 403)
