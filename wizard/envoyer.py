from  odoo import models, fields, api


class Envoyer(models.TransientModel):
    _name = "mission.envoyer"
    _description = "Envoie Email"
    _order = 'id desc'

    message = fields.Html(string="Message")
    ordre_mission = fields.Binary(string="Ordre de Mission", required=True)
    ordre_mission_name = fields.Char(string="Ordre de Mission File")

    def action_send_etat_signer_mission_by_email(self):
        send_notification = "Email envoyé avec succès"
        template = self.env.ref("mission.etat_liquidatif_signer_mission")
        if template:
            self.env["mail.template"].browse(template.id).sudo().send_mail(
                self.id, force_send=True
            )
            self.env["mail.mail"].sudo().process_email_queue()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': send_notification,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }




