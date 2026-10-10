import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from mcp.server import MCPServer

load_dotenv()

mcp = MCPServer(
    "Email MCP",
    instructions="Provides bounded tools for composing and sending emails."
)


def validate_email(address: str) -> str:
    address = address.strip()

    if not address:
        raise ValueError("Recipient email cannot be empty.")

    if "@" not in address:
        raise ValueError("Invalid email address.")

    return address


def validate_subject(subject: str) -> str:
    subject = subject.strip()

    if not subject:
        raise ValueError("Email subject cannot be empty.")

    if len(subject) > 200:
        raise ValueError("Email subject is too long.")

    return subject


def validate_body(body: str) -> str:
    body = body.strip()

    if not body:
        raise ValueError("Email body cannot be empty.")

    return body


@mcp.tool()
def write_email(
    recipient: str,
    subject: str,
    body: str,
) -> dict:
    """
    Create and validate an email draft without sending it.

    Use this tool when the user wants to compose an email
    but has not asked to send it yet.
    """

    recipient = validate_email(recipient)
    subject = validate_subject(subject)
    body = validate_body(body)

    return {
        "status": "draft",
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }


@mcp.tool()
def send_email(
    recipient: str,
    subject: str,
    body: str,
) -> dict:
    """
    Send an email to the specified recipient.

    The SMTP credentials are configured on the MCP server
    and are never provided by the LLM.
    """

    recipient = validate_email(recipient)
    subject = validate_subject(subject)
    body = validate_body(body)

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM")

    if not smtp_host:
        raise RuntimeError("SMTP_HOST is not configured.")

    if not smtp_username:
        raise RuntimeError("SMTP_USERNAME is not configured.")

    if not smtp_password:
        raise RuntimeError("SMTP_PASSWORD is not configured.")

    if not email_from:
        raise RuntimeError("EMAIL_FROM is not configured.")

    message = EmailMessage()

    message["From"] = email_from
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(body)

    try:
        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=10,
        ) as smtp:

            smtp.starttls()

            smtp.login(
                smtp_username,
                smtp_password,
            )

            smtp.send_message(message)

        return {
            "status": "sent",
            "recipient": recipient,
            "subject": subject,
            "message": "Email sent successfully.",
        }

    except (smtplib.SMTPException, OSError) as error:

        return {
            "status": "error",
            "recipient": recipient,
            "subject": subject,
            "message": f"Email could not be sent: {error}",
        }


app = mcp.streamable_http_app()