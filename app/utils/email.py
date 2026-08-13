import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import Config


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email:
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = Config.MAIL_DEFAULT_SENDER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        if Config.MAIL_USE_TLS:
            server.starttls()
        if Config.MAIL_USERNAME and Config.MAIL_PASSWORD:
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.sendmail(Config.MAIL_DEFAULT_SENDER, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email para {to_email}: {e}")
        return False


def send_password_reset_email(email: str, code: str, doctor_name: str) -> bool:
    body = f"""
Olá {doctor_name},

Você solicitou a recuperação de senha da sua conta.

Seu código de verificação é: {code}

Este código expira em 1 hora.

Se você não solicitou esta recuperação, ignore este email.

Atenciosamente,
MedSinc
"""
    return send_email(email, "MedSinc - Recuperação de Senha", body)


def send_new_application_email(
    *,
    to_email: str,
    staff_name: str,
    doctor_name: str,
    hospital_name: str,
    opportunity_date: str,
    specialty: str,
) -> bool:
    body = f"""
Olá {staff_name},

{doctor_name} se candidatou a um plantão no {hospital_name}.

Data: {opportunity_date}
Especialidade: {specialty}

Acesse o portal hospitalar MedSinc para analisar a candidatura.

Atenciosamente,
MedSinc
"""
    return send_email(to_email, "MedSinc - Nova candidatura a plantão", body)


def send_application_approved_email(
    *,
    to_email: str,
    doctor_name: str,
    hospital_name: str,
    opportunity_date: str,
    start_time: str,
    end_time: str,
    specialty: str,
) -> bool:
    body = f"""
Olá {doctor_name},

Sua candidatura foi aprovada!

Hospital: {hospital_name}
Data: {opportunity_date}
Horário: {start_time} – {end_time}
Especialidade: {specialty}

O plantão já aparece na sua agenda MedSinc.

Atenciosamente,
MedSinc
"""
    return send_email(to_email, "MedSinc - Candidatura aprovada", body)


def send_application_rejected_email(
    *,
    to_email: str,
    doctor_name: str,
    hospital_name: str,
    opportunity_date: str,
    specialty: str,
) -> bool:
    body = f"""
Olá {doctor_name},

Sua candidatura ao plantão abaixo não foi selecionada desta vez.

Hospital: {hospital_name}
Data: {opportunity_date}
Especialidade: {specialty}

Continue acompanhando novas vagas no marketplace MedSinc.

Atenciosamente,
MedSinc
"""
    return send_email(to_email, "MedSinc - Atualização da candidatura", body)
