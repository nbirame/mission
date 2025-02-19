from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError


class Suivi(models.Model):
    _name = "mission.suivi_essence"
    _description = "Suivi du niveau d'essence"

    vehicle_id = fields.Many2one("fleet.vehicle", string="Véhicule")
    source = fields.Selection([
        ('Carte', 'Carte'),
        ('Ticket', 'Ticket')
    ],
        'Source',
        default='Carte'
    )
    carte_id = fields.Many2one("carburant.cartecarburant", string="Selectionner la carte de carburant")
    number_liter = fields.Float(string="Nombre de Litre", required=True)
    liter_price = fields.Float(string="Prix au Litre", required=True)
    total_price = fields.Float(string="Prix Total", compute="_compute_total_price", store=True)
    mileage = fields.Float(string="Kilométrage", required=True)
    date_of_departure = fields.Datetime(string="Date et heure", required=True)
    time_of_departure = fields.Char(string="Heure de depart", compute="_compute_time_of_departure", store=True)
    date_of_departure_format = fields.Char(string="Date", compute="_compute_date_of_departure_format", store=True)
    conducteur_id = fields.Many2one("res.partner", string="Conducteur")
    destination = fields.Html(string="Destination", required=True)
    obsevation = fields.Html(string="Observations")
    note = fields.Html(string="Commentaire", help="Ecrivez ici toute information")
    number_suivi = fields.Integer(string="Suivi", compute="_get_count_suivi", store=True)

    @api.depends("liter_price", "number_liter")
    def _compute_total_price(self):
        for record in self:
            if record.number_liter and record.liter_price:
                record.total_price = record.liter_price * record.number_liter

    @api.depends("date_of_departure")
    def _compute_time_of_departure(self):
        for record in self:
            if record.date_of_departure:
                record.time_of_departure = datetime.strptime(str(record.date_of_departure),
                                                             "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")

    @api.depends("date_of_departure")
    def _compute_date_of_departure_format(self):
        for record in self:
            if record.date_of_departure:
                record.date_of_departure_format = datetime.strptime(str(record.date_of_departure),
                                                                    "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")

    def name_get(self):
        info_suivi = []
        for record in self:
            rec_name = "%s-%s" % (record.vehicle_id.name, record.conducteur_id.name)
            info_suivi.append((record.id, rec_name))
        return info_suivi

    @api.model
    def create(self, vals):
        res = super(Suivi, self).create(vals)
        if res.mileage:
            data = {'value': res.mileage, 'date': res.date_of_departure, 'vehicle_id': res.vehicle_id.id,
                    'conducteur_id': res.conducteur_id.id}
            self.env['fleet.vehicle.odometer'].create(data)
        else:
            data = {'date': res.date_of_departure, 'vehicle_id': res.vehicle_id.id,
                    'conducteur_id': res.conducteur_id.id}
            self.env['fleet.vehicle.odometer'].create(data)
        if res.carte_id:
            consomation_data = {'nb_littre': res.number_liter, 'prix': res.liter_price,
                                'vehicule_id': res.vehicle_id.id, 'carte_id': res.carte_id.id, 'total': res.total_price}
            self.env['carburant.consommation'].create(consomation_data)
        else:
            consomation_data = {'nb_littre': res.number_liter, 'prix': res.liter_price,
                                'vehicule_id': res.vehicle_id.id, 'carte_id': res.carte_id.id, 'total': res.total_price}
            self.env['carburant.consommation'].create(consomation_data)
        return res

    # @api.model
    def write(self, vals):
        # domain = []
        data = {'value': self.mileage, 'date': self.date_of_departure, 'vehicle_id': self.vehicle_id,
                'conducteur_id': self.conducteur_id}
        if 'mileage' in vals:
            data['value'] = vals.get('mileage')
        if 'date_of_departure' in vals:
            data['date'] = vals.get('date_of_departure')
        if 'vehicle_id' in vals:
            data['vehicle_id'] = vals.get('vehicle_id')
        if 'conducteur_id' in vals:
            data['conducteur_id'] = vals.get('conducteur_id')
        value = self.mileage
        date = self.date_of_departure
        vehicle_id = self.vehicle_id.id
        conducteur_id = self.conducteur_id.id
        odometre = self.env["fleet.vehicle.odometer"].sudo().search([("value", "=", value),
                                                                     ("vehicle_id", "=", vehicle_id),
                                                                     ("date", "=", date),
                                                                     ("conducteur_id", "=", conducteur_id)])
        if odometre:
            odometre.write(data)
        else:
            raise ValidationError(_("Sorry this entrie does not existe"))
        res = super(Suivi, self).write(vals)
        return res

    @api.depends("vehicle_id")
    def _get_count_suivi(self):
        for record in self:
            record.number_suivi = self.env['mission.suivi_essence'].search_count(
                [('vehicle_id', '=', record.vehicle_id.id)])
            self.vehicle_id.write({'suivi_count': record.number_suivi})
