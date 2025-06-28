import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

def send_password_reset_email(email: str, code: str, doctor_name: str):
    subject = "MedSinc - Recuperação de Senha"
    body = f"""
    Olá {doctor_name},
    
    Você solicitou a recuperação de senha da sua conta.
    
    Seu código de verificação é: {code}
    
    Este código expira em 1 hora.
    
    Se você não solicitou esta recuperação, ignore este email.
    
    Atenciosamente,
    MedSinc
    """
    
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.MAIL_DEFAULT_SENDER
        msg['To'] = email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(Config.MAIL_DEFAULT_SENDER, email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False 