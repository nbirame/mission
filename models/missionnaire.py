from  odoo import fields, models


class Missionnaire(models.Model):
    _name = "mission.missionnaire"
    _description = "Missionnaire"

    name = fields.Char(string="Type missionnaire", default="AGENT")