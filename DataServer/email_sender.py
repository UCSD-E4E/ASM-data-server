import smtplib
from email.message import EmailMessage
class email_sender:
    
    def __init__(self, logger, subject=None, body=None, configDict=None) -> None:
        if configDict is not None:
            self.username = configDict['email_username']
            self.password = configDict['email_password']
            self.send_to = configDict['eamil_receiver']
            self.subject = configDict['email_subject']
            self.body = configDict['email_content']
        else: 
            raise RuntimeError('Need to pass the configDict to instantiate the email')
        if subject is not None: 
            self.subject = subject
            
        if body is not None:
            self.body = body
      
        self._log = logger
    
    def update(self, new_subject=None, new_body=None, new_receiver=None):
        if new_subject is not None:
            assert isinstance(new_subject,str)
            self.subject = new_subject
        if new_body is not None:
            assert isinstance(new_body,str)
            self.body = new_body
        if new_receiver is not None:
            assert isinstance(new_receiver, list)
            self.send_to = new_receiver  

    def send_email(self):        

        # email_text = """\
        # From: %s
        # To: %s
        # Subject: %s

        # %s
        # """ % (sent_from, ", ".join(to), subject, body)
        email_text = EmailMessage()
        email_text.set_content(self.body)
        email_text['Subject'] = self.subject
        email_text['From'] = self.username
        email_text['To'] = ', '.join(self.send_to)

        try:
            smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            smtp_server.ehlo()
            smtp_server.login(self.username, self.password)
            # smtp_server.sendmail(sent_from, to, email_text)
            smtp_server.send_message(email_text)
            smtp_server.close()
            self._log.info ("Email sent successfully!")
            return 0
        except Exception as ex:
            self._log.info ("Something went wrong….",ex)
            return 1
