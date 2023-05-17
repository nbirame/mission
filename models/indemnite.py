from odoo import models, fields, api, _


class Indemnite(models.Model):
    _name = "mission.indemnite"
    _description = "Indemnité journalière d'une mission"

    montant = fields.Integer(string="Indemnité journalière")
    missionnaire_id = fields.Many2one("mission.missionnaire", string="Missionnaire")
    type_mission_id = fields.Many2one("mission.type_mission", string="Type de Mission")
    zone_id = fields.Many2one("mission.zone", string="Zone de Mission")

    def name_get(self):
        indemnite = []
        for record in self:
            rec_name = "%s" % (record.montant)
            indemnite.append((record.id, rec_name))
        return indemnite
