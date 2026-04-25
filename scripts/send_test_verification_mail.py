from app.auth import _verification_email_content, send_email


if __name__ == "__main__":
    subject, body, html_body = _verification_email_content("Burak Boysan", "123456")
    result = send_email("burakboysan@bomaksan.com", subject, body, html_body)
    print(result)
