# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta


class Delegation(models.Model):
    _name = 'mission.delegation'
    _description = 'Délégué de Mission'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Numéro de mission", readonly=True, store=True)
    type_mission_id = fields.Many2one("mission.type_mission", string="Type de mission")
    zone_id = fields.Many2one("mission.zone", string="Zone")
    motif = fields.Text(string="Motifs", required=True)
    lettre = fields.Binary(string="Lettre de mission")
    chef = fields.Many2one("hr.employee", string="Chef de mission", required=True)
    trajet = fields.Char(string="Trajet", required=True)
    moyen_transport = fields.Selection([
        ('Voiture', 'Voiture'), ('Avion', 'Avion'), ('Bateau', 'Bateau'), ('Train', 'Train'),
    ],
        'Moyen de Transport', default='Voiture'
    )
    date_depart = fields.Date(string="Date de départ", required=True, default=fields.Date.today, tracking=True, )
    date_retour = fields.Date(string="Date de retour", required=True, tracking=True, )
    lieu_depart = fields.Many2one("mission.adresse", string="Lieu de départ", required=True)
    lieu_arrive = fields.Many2one("mission.adresse", string="Lieu d'arrivée", required=True)
    distance = fields.Integer(string="Distance aller-retour en KM", compute="_compute_distance", store=True)
    duree = fields.Integer(string="Durée", compute="_compute_duree", store=True)
    nb_nuit = fields.Integer(string="Nombre de nuit", compute="_compute_nb_nuit", store=True)
    carburant = fields.Float(string="Nombre de littres carburant nécessaire", store=True)
    observation = fields.Text(string="Observation")
    total_perdieme = fields.Integer(string="Total perdieme", compute="_compute_total_perdieme", store=True)
    cout_mission = fields.Integer(string="Cout de la mission", compute="_compute_cout_mission", store=True)
    equipe_id = fields.One2many("mission.equipe", "mission_id", string="Equipe de la mission", store=True)
    vehicule_id = fields.One2many("mission.vehicle", "mission_id", string="Les Véhicule de la mission")
    consommation_id = fields.One2many("mission.consommation", "delegation_id", string="Consomation", store=True)
    source = fields.Selection(
        [
            ('Cart', 'Carte'), ('Ticket', 'Ticket'),
        ],
        'Source', default="Cart"
    )
    nombre_ticket = fields.Integer(string="Nombre de tickets")
    prix_littre = fields.Float(string="Prix en (FCFA)", store=True)
    cout_ticket = fields.Float(string="Cout Tickets", store=True)
    cout_carburant = fields.Float(string="Cout du carburant", compute="_compute_cout_carburant", store=True)
    dotation_carburant = fields.Float(string="Dotation carburant", compute="_compute_dotation_carburant", store=True)
    cartecarburant_id = fields.Many2one("mission.cartecarburant", string="Choisir la carte de carburant")
    state = fields.Selection([
        ('programmer', 'Brouillon'),
        ('confirmer', 'Confirmer'),
        ('en_cours', 'En cours'),
        ('terminer', 'Terminer'),
    ],
        default='programmer', store=True, string="Status")
    rapport_mission = fields.Binary(string="Rapport de la Mission")
    rapport_mission_name = fields.Char(string="Rapport de la Mission")
    ordre_mission = fields.Binary(string="Ordre de la Mission")
    ordre_mission_name = fields.Char(string="Ordre de la Mission")

    # contrainte pour éviter qu'un employé soit dans deux équipes de mission dans une meme période
    @api.constrains("chef", "date_depart", "date_retour")
    def _check_chef(self):
        missions = self.env["mission.delegation"].sudo().search([('chef', '=', self.chef.id)])
        for record in self:
            for mission in missions[:-1]:
                if (
                        (mission.date_depart <= record.date_depart < mission.date_retour) or (
                        mission.date_depart <= record.date_retour < mission.date_retour) or (
                                record.date_depart <= mission.date_depart < record.date_retour)):
                    if mission.chef.id == record.chef.id:
                        raise ValidationError(_("Le chef de mission doit être en mission pendant cette période"))

    @api.depends("lieu_arrive")
    def _compute_distance(self):
        for record in self:
            record.distance = record.lieu_arrive.distance

    @api.onchange("distance")
    def _onchange_carburant(self):
        for record in self:
            record.carburant = (record.distance * 15) / 100

    # Methode qui permet de calculer la durée à partir de deux dates(Date de retour  et date de départ)
    @api.depends("date_depart", "date_retour")
    def _compute_duree(self):
        for record in self:
            if record.date_depart and record.date_retour:
                date_ret = datetime.strptime(str(record.date_retour), "%Y-%m-%d").strftime("%Y,%m,%d")
                date_dep = datetime.strptime(str(record.date_depart), "%Y-%m-%d").strftime("%Y,%m,%d")
                date_ret = date_ret.split(',')
                date1 = datetime(int(date_ret[0]), int(date_ret[1]), int(date_ret[2]))
                date_dep = date_dep.split(',')
                date2 = datetime(int(date_dep[0]), int(date_dep[1]), int(date_dep[2]))

                diff = date1 - date2
                if int(diff.days) >= 0:
                    record.duree = diff.days
                else:
                    record.duree = 0
                    # print(record.duree)
                    raise ValidationError(_("La date de retoure ne doit pas etre antérieure au date de départ "))



    @api.depends("duree")
    def _compute_nb_nuit(self):
        for record in self:
            if record.duree:
                record.nb_nuit = record.duree - 1

    # methode qui permet de créer une mission authomatiquement avec un numero de séquence générer
    @api.model
    def create(self, values):
        values["name"] = (
                self.env["ir.sequence"].next_by_code("mission.delegation") or "/"
        )
        res = super(Delegation, self).create(values)
        return res

    @api.onchange("cartecarburant_id")
    def _onchange_prix_littre(self):
        for record in self:
            if record.cartecarburant_id:
                record.prix_littre = record.cartecarburant_id.chargement_ids[-1].prix

    @api.depends('consommation_id')
    def _compute_cout_carburant(self):
        cons = []
        for record in self:
            for consommation in record.consommation_id:
                cons.append(consommation.total)
                record.cout_carburant = sum(cons)

    @api.depends('equipe_id')
    def _compute_total_perdieme(self):
        res = []
        for record in self:
            for equipe in record.equipe_id:
                res.append(equipe.total)
                record.total_perdieme = sum(res)

    @api.depends("vehicule_id", "carburant")
    def _compute_dotation_carburant(self):
        for record in self:
            if record.vehicule_id:
                record.dotation_carburant = len(record.vehicule_id) * record.carburant

    @api.depends("total_perdieme", "cout_carburant", "cout_ticket")
    def _compute_cout_mission(self):
        for record in self:
            if record.nombre_ticket:
                record.cout_mission = record.total_perdieme + record.cout_ticket
            else:
                record.cout_mission = record.total_perdieme + record.cout_carburant

    @api.onchange("prix_littre", "nombre_ticket")
    def _onchange_cout_ticket(self):
        for record in self:
            record.cout_ticket = record.prix_littre * record.nombre_ticket

    # méthode qui permet de créer une consommation en fonction de des véhicules de la mission,
    # le nombre de littre de carburant pour le voyage et la carte de carburant utiliser
    @api.onchange('vehicule_id', 'carburant', 'cartecarburant_id')
    def _onchange_consommation_id(self):
        for record in self:
            lines = [(5, 0, 0)]
            if self.vehicule_id:
                for veh in record.vehicule_id:
                    consommation_record = {
                        'nb_littre': record.carburant,
                        'prix': record.prix_littre,
                        'total': record.equipe_id[0].total,
                        'vehicule_id': veh.voiture_id.id,
                        'delegation_id': record.id,
                        'carte_id': record.cartecarburant_id.id
                    }
                    lines.append((0, 0, consommation_record))
            record.consommation_id = lines

    # méthode qui permet d'ajouter une equipe de mission de façon automatique
    @api.onchange("chef", "type_mission_id", "zone_id", "nb_nuit")
    def _onchange_equipe_id(self):
        for record in self:
            personal_equipe = [(5, 0, 0)]
            if not record.equipe_id:
                if record.chef or record.nb_nuit:
                    personal_record = {
                        'employee_id': record.chef.id,
                        'mission_id': record.id,
                    }
                    personal_equipe.append((0, 0, personal_record))
            else:
                if record.chef or record.nb_nuit:
                    personal_record_one = {
                        'employee_id': record.chef.id,
                        'type_missionnaire_id': record.equipe_id[0].type_missionnaire_id.id,
                        'mission_id': record.id,
                    }
                    personal_equipe.append((0, 0, personal_record_one))

                    for equipe in record.equipe_id[1::]:
                        personal_record = {
                            'employee_id': equipe.employee_id.id,
                            'type_missionnaire_id': equipe.type_missionnaire_id.id,
                            'mission_id': record.id,
                        }
                        personal_equipe.append((0, 0, personal_record))
            self.equipe_id = personal_equipe

    # action du workflow pour une mission en brouillon
    def action_programmer(self):
        self.write({'state': 'programmer'})

    # action du workflow pour une mission en confirmer
    def action_confirmer(self):
        self.write({'state': 'confirmer'})

    # action du workflow pour une mission en en cours
    def action_en_cours(self):
        self.write({'state': 'en_cours'})
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "en_mission"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    # action du workflow pour une mission terminer
    def action_terminer(self):
        self.write({'state': 'terminer'})
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "disponible"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "disponible"})

    # methode qui permet d'imprimer le report de l'equipe de mission
    def print_report_agent(self):
        return self.env.ref("mission.report_mission_delegation_agent").report_action(self)

    # methode qui permet d'imprimer le report de l'ordre de mission
    def print_report_mission(self):
        return self.env.ref("mission.report_mission_delegation").report_action(self)

    def import_data(self):
        return self.env.ref("odoo.addons.base_import.models.base_import.ImportRecords")

    # contrainte qui permet de ne pas choisir une carte de carburant qui n'a pas
    # le nombre de littre nécessaire pour le voyage
    @api.constrains("cartecarburant_id", "carburant")
    def _check_cartecarburant_id(self):
        cartes = self.env["mission.delegation"].sudo().search([('cartecarburant_id', '=', self.cartecarburant_id.id)])
        if self.cartecarburant_id:
            for carte in cartes:
                if carte.cartecarburant_id.restant_littre < self.carburant:
                    raise ValidationError(_(f"La carte ne contient pas le nombre de littres nécessaire pour le "
                                            f"voyage"))

    # méthode qui permet l'envoie d'email en appelant le report de template email_template_equipe_mission
    def action_send_mission_by_email(self):
        notif_message = "Email envoyé avec succès"
        template = self.env.ref("mission.email_template_equipe_mission")
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
                    'message': notif_message,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }

    def action_send_etat_mission_by_email(self):
        send_notification = "Email envoyé avec succès"
        template = self.env.ref("mission.etat_liquidatif_mission")
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

    def con_mission_state_method(self):
        date_today = datetime.today().date()
        mission_programmers = self.env['mission.delegation'].sudo().search([('date_depart', '=', date_today)])
        for status_mission in mission_programmers:
            if status_mission.state == 'confirmer':
                status_mission.state = "en_cours"
        mission_en_cours = self.env['mission.delegation'].sudo().search([('date_retour', '=', date_today)])
        for status_mission in mission_en_cours:
            if status_mission.state == 'en_cours':
                status_mission.state = "terminer"
        return True

    def etat_mission_state_method(self):
        missions_confirmer = self.env['mission.delegation'].sudo().search([('state', '=', 'confirmer')])
        if missions_confirmer:
            self.action_send_mission_by_email()

    def equipe_mission_state_method(self):
        missions_confirmer = self.env['mission.delegation'].sudo().search([('state', '=', 'confirmer')])
        if missions_confirmer:
            # self.action_send_etat_mission_by_email()
            send_notification = "Email envoyé avec succès"
            template = self.env.ref("mission.etat_liquidatif_mission")
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

    # def import_data_file(self):
    #     return Import.get_fields_tree