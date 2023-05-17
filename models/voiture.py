from odoo import fields, models, api


class Voiture(models.Model):
    # _name = "mission.voiture"
    _description = "Voiture de Mission"
    _inherit = "fleet.vehicle"

    mission_id = fields.Many2one("mission.delegation",  string="Mission")
    state = fields.Selection([
        ('en_mission', 'en_mission'),
        ('disponible', 'disponile')
    ], "Etat", default="disponible")
    suivi_count = fields.Integer(string="Nombre de Deplacement")
    conducteur_id = fields.Many2one("res.partner", string="Chauffeur")

    def return_action_to_open_suivi(self):
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:

            res = self.env['ir.actions.act_window']._for_xml_id('mission.%s' % xml_id)
            res.update(
                context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                domain=[('vehicle_id', '=', self.id)]
            )
            return res
        return False

