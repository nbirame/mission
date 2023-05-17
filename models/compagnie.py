from odoo import models, fields, api, _


class Compagnie(models.Model):
    _name = "mission.compagnie"
    _description = "Compagnie de Mission"

    name = fields.Char(strin="Compagnie")
    employee_id = fields.Many2one("hr.employee", string="Emplyé")
    ticket = fields.Float(string="Billet de Voyage")
    ticket_number = fields.Integer(string="Nombre de Billet")
    total = fields.Float(string="Prix Total")
    delegation_id = fields.Many2one("mission.delegation", string="Mission")

    @api.onchange('ticket', 'ticket_number')
    def _onchange_total(self):
        for record in self:
            if record.ticket and record.ticket_number:
                record.total = record.ticket * record.ticket_number
