from  odoo import fields, models


class Missionnaire(models.Model):
    _name = "mission.missionnaire"
    _description = "Missionnaire"

    name = fields.Char(string="Type missionnaire", default="AGENT")

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Le type de missionnaire doit etre unique')
    ]