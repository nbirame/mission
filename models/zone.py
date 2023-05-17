from odoo import fields, models, api


class Zone(models.Model):
    _name = "mission.zone"
    _description = "Zone de Mission "

    description = fields.Html(string="Description")
    zone_mission = fields.Char(string="Zone")

    def name_get(self):
        zo = []
        for record in self:
            rec_name = "%s" % (record.zone_mission)
            zo.append((record.id, rec_name))
        return zo
