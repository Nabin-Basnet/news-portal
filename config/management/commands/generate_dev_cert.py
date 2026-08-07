"""Create a self-signed certificate for local Django HTTPS development."""
from __future__ import annotations
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Create a self-signed localhost certificate in .certs/."

    def handle(self, *args, **options):
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except ImportError as exc:
            raise CommandError("This command requires cryptography. Run `pip install -r requirements.txt`.") from exc
        certificate_dir = Path(settings.BASE_DIR) / ".certs"
        certificate_dir.mkdir(exist_ok=True)
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(issuer)
            .public_key(private_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc) - timedelta(minutes=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(private_key, hashes.SHA256()))
        (certificate_dir / "localhost-key.pem").write_bytes(private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        (certificate_dir / "localhost-cert.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        self.stdout.write(self.style.SUCCESS(f"Created {certificate_dir}"))
