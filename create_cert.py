import datetime
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


# 센서값을 https를 통하지 않고 전송할 수 없으므로 https 사설 인증서 발급
def generate_self_signed_cert():
    print("Generating self-signed certificate...")
    
    # 1. 개인키 생성
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # 2. 인증서 정보 (Subject/Issuer)
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COUNTRY_NAME, u"KR"),
        x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, u"IMU Local Server"),
        x509.NameAttribute(x509.NameOID.COMMON_NAME, u"localhost"),
    ])
    
    # 3. 인증서 빌드
    cert = x509.CertificateBuilder().subject_name(subject).issuer_name(issuer).public_key(
        key.public_key()
    ).serial_number(x509.random_serial_number()).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())

    # 4. 파일 저장
    with open("key.pem", "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("Done! 'cert.pem' and 'key.pem' created.")

if __name__ == "__main__":
    generate_self_signed_cert()