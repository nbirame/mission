# -*- coding: utf-8 -*-
import num2words as num2words
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import ValidationError
from math import ceil
from num2words import num2words
import calendar


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
    moyen_transport = fields.Selection([('Voiture', 'Voiture'), ('Avion', 'Avion'), ('Bateau', 'Bateau'),
                                        ('Train', 'Train'),
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
    cout_mission = fields.Integer(string="Cout de la mission", compute="_depends_cout_mission", store=True)
    equipe_id = fields.One2many("mission.equipe", "mission_id", string="Equipe de la mission", store=True)
    vehicule_id = fields.One2many("mission.vehicle", "mission_id", string="Les Véhicule de la mission", store=True)
    consommation_id = fields.One2many("carburant.consommation", "delegation_id", string="Consomation", store=True)
    source = fields.Selection(
        [
            ('Cart', 'Carte'), ('Ticket', 'Ticket'),
        ],
        'Source', default="Cart"
    )
    nombre_ticket = fields.Integer(string="Nombre de tickets", store=True)
    prix_littre = fields.Float(string="Prix en (FCFA)", store=True)
    cout_ticket = fields.Float(string="Cout Tickets", store=True)
    cout_carburant = fields.Float(string="Cout du carburant", compute="_compute_cout_carburant", store=True)
    dotation_carburant = fields.Float(string="Dotation carburant", compute="_compute_dotation_carburant", store=True)
    cartecarburant_id = fields.Many2one("carburant.cartecarburant", string="Choisir la carte de carburant")
    state = fields.Selection([
        ('programmer', 'Brouillon'),
        ('confirmer', 'Confirmée'),
        ('en_cours', 'En cours'),
        ('terminer', 'Terminée'),
        ('annuler', 'Annulée'),
    ],
        default='programmer', store=True, string="Status")
    rapport_mission = fields.Binary(string="Rapport de la Mission")
    rapport_mission_name = fields.Char(string="Rapport de la Mission", store=True,)
    # ordre_mission = fields.Binary(string="Ordre de la Mission")
    # ordre_mission_name = fields.Char(string="Ordre de la Mission")

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
                        if mission.chef.state == "en_mission":
                            raise ValidationError(_("Le chef de mission doit être en mission pendant cette période"))

    @api.constrains('equipe_id', 'date_depart', 'date_retour')
    def _check_equipe_id(self):
        for mission in self:
            # Calcul du nombre de jours de la nouvelle mission
            new_mission_days = (mission.date_retour - mission.date_depart).days + 1
            if new_mission_days < 0:
                raise ValidationError(_("La date de retour doit être supérieure ou égale à la date de départ.Le nombre de jour %(nombre)s", nombre=new_mission_days))

            # Récupération de toutes les missions du mois (sauf la mission en cours d'édition)
            month_missions = self.env['mission.delegation'].sudo().search([
                ('id', '!=', mission.id),
                ('date_depart', '<=', mission.get_month_end()),
                ('date_retour', '>=', mission.get_month_start()),
            ])

            # Parcourir chaque membre de l'équipe
            for membre in mission.equipe_id:
                # Récupérer les missions du mois où ce membre apparaît
                membre_missions = month_missions.filtered(
                    lambda m: membre.id in m.equipe_id.ids
                )

                # Calculer le total de jours déjà pris par ce membre sur le mois
                total_days_for_membre = sum(
                    (m.date_retour - m.date_depart).days + 1
                    for m in membre_missions
                )
                if total_days_for_membre:
                    raise ValidationError(_(
                        "Le membre %(membre)s dépasse le quota de 10 %(nombre)s jours de mission pour ce mois.",
                        membre=membre.employee_id.name, nombre=total_days_for_membre
                    ))
                else:
                    raise ValidationError(_(
                        "Le membre %(membre)s dépasse le quota de 10 jours de mission pour ce mois %(mission)s. %(nombre)s les missions sont %(mem)s:",
                        membre=membre.employee_id.name, mission=month_missions, nombre=total_days_for_membre, mem=membre_missions
                    ))
                # Vérification : si le total existant + la nouvelle mission > 10
                if total_days_for_membre + new_mission_days > 10:
                    raise ValidationError(_(
                        "Le membre %(membre)s dépasse le quota de 10 jours de mission pour ce mois.",
                        membre=membre.name
                    ))

    @api.depends("lieu_arrive")
    def _compute_distance(self):
        for record in self:
            record.distance = record.lieu_arrive.distance * 2

    @api.onchange('type_mission_id')
    def _onchange_zone_id(self):
        for record in self:
            if record.type_mission_id.type_miss == 'Interieur' or \
                    record.type_mission_id.type_miss == 'interieur' or \
                    record.type_mission_id.type_miss == 'intérieur' or \
                    record.type_mission_id.type_miss == 'Intérieure' or \
                    record.type_mission_id.type_miss == 'intérieure' or \
                    record.type_mission_id.type_miss == 'interne' or record.type_mission_id.type_miss == 'Interne':
                record.zone_id = False

    @api.onchange("distance")
    def _onchange_carburant(self):
        for record in self:
            record.carburant = (record.distance * 15) / 100

    @api.onchange("carburant", "source", "moyen_transport", "consommation_id")
    def _onchange_nombre_ticket(self):
        nombre_cons = 1
        for record in self:
            if record.consommation_id:
                nombre_cons = len(record.consommation_id)
            if record.carburant and record.source == "Ticket":
                record.nombre_ticket = ceil(record.carburant / 10) * nombre_cons
                record.cartecarburant_id = False
                record.cout_carburant = record.cout_ticket
            else:
                record.nombre_ticket = 0

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
                    nombre_jour = diff.days + 1
                    if nombre_jour <= 10:
                        record.duree = nombre_jour
                    else:
                        raise ValidationError(_("Le nombre de jours de mission ne doit pas depasser 10 jours"))
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

    @api.onchange("cartecarburant_id", "moyen_transport")
    def _onchange_prix_littre(self):
        for record in self:
            if record.cartecarburant_id and record.moyen_transport == "Voiture":
                if record.cartecarburant_id.chargement_ids:
                    record.prix_littre = record.cartecarburant_id.chargement_ids[-1].prix
                else:
                    ValidationError(_("Veillez charger la carte"))

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
            else:
                record.dotation_carburant = 0

    @api.depends('consommation_id', 'source')
    def _compute_cout_carburant(self):
        cons = []
        for record in self:
            if record.consommation_id:
                nombre_cons = len(record.consommation_id)
                if record.source == "Cart":
                    record.cout_carburant = nombre_cons * record.prix_littre * record.carburant
                    record.cout_ticket = 0
                else:
                    record.cout_carburant = record.cout_ticket * nombre_cons
            else:
                record.cout_carburant = 0

    @api.depends("total_perdieme", "consommation_id", "moyen_transport")
    def _depends_cout_mission(self):
        for record in self:
            if record.cout_carburant or record.cout_ticket:
                record.cout_mission = record.total_perdieme + record.cout_carburant + record.cout_ticket
            else:
                record.cout_mission = record.total_perdieme

    @api.onchange("prix_littre", "nombre_ticket")
    def _onchange_cout_ticket(self):
        for record in self:
            record.cout_ticket = record.prix_littre * record.nombre_ticket * 10

    # méthode qui permet de créer une consommation en fonction de des véhicules de la mission,
    # le nombre de littre de carburant pour le voyage et la carte de carburant utiliser
    @api.onchange('vehicule_id', 'carburant', 'cartecarburant_id', 'prix_littre', 'source', 'moyen_transport')
    def _onchange_consommation_id(self):
        for record in self:
            lines = [(5, 0, 0)]
            if record.vehicule_id:
                for veh in record.vehicule_id:
                    if record.source == "Cart":
                        consommation_record = {
                            'nb_littre': record.carburant,
                            'prix': record.prix_littre,
                            'total': record.prix_littre * record.carburant,
                            'vehicule_id': veh.voiture_id.id,
                            'delegation_id': record.id,
                            'carte_id': record.cartecarburant_id.id
                        }
                    else:
                        consommation_record = {
                            'nb_littre': record.carburant,
                            'prix': record.prix_littre,
                            'total': record.cout_ticket,
                            'vehicule_id': veh.voiture_id.id,
                            'delegation_id': record.id,
                            'carte_id': record.cartecarburant_id.id
                        }
                    lines.append((0, 0, consommation_record))
            record.consommation_id = lines
            if record.moyen_transport == 'Avion' or record.moyen_transport == 'Bateau' or record.moyen_transport == 'Train':
                record.cartecarburant_id = False
                record.nombre_ticket = 0
                record.prix_littre = 0
                record.source = ''
                self.env['mission.vehicle'].sudo().search([('mission_id', '=', self.name)]).unlink()

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
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    # action du workflow pour une mission en confirmer
    def action_confirmer(self):
        self.write({'state': 'confirmer'})
        self.action_send_email_etat_mission("email_template_equipe_mission")
        self.action_send_email_etat_mission("etat_liquidatif_mission")
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})
        # self.action_send_mission_by_email()

    def action_annuler(self):
        self.write({'state': 'annuler'})
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "disponible"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "disponible"})
        self.chef.write({'state': "disponible"})

    # action du workflow pour une mission en en cours
    def action_en_cours(self):
        self.write({'state': 'en_cours'})
        # self.action_send_mission_by_email()
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.sudo().write({'state': "en_mission"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "en_mission"})
        self.chef.write({'state': "en_mission"})

    # action du workflow pour une mission terminer
    def action_terminer(self):
        self.write({'state': 'terminer'})
        self.action_send_email_etat_mission("etat_liquidatif_mission")
        for vehicle in self.vehicule_id:
            vehicle.voiture_id.write({'state': "disponible"})
        for employee in self.equipe_id:
            employee.employee_id.write({'state': "disponible"})
        self.chef.write({'state': "disponible"})

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

    def envoie_email_method(self):
        notif_message = "Email envoyé avec succès"
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        template = self.env.ref("mission.%s" % xml_id)
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

    def action_send_email_etat_mission(self, temp):
        send_notification = "Email envoyé avec succès"
        # template = self.env.ref("mission.etat_liquidatif_mission")
        template = self.env.ref("mission.%s" % temp)
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

    def convert_number_to_words(self, avance):
        number_text = num2words(avance, lang="fr")
        return number_text

    def get_manager(self, groupe):
        manager = []
        users = self.env['res.users'].sudo().search([])
        for user in users:
            if user.has_group(groupe):
                employe = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
                if employe:
                    manager.append(employe.work_email)
        return ';'.join(manager)

    def get_rh(self):
        return self.get_manager('mission.group_mission_rh')

    def get_daf(self):
        return self.get_manager('mission.group_mission_daf')

    def get_imputation_bugetaire(self):
        budgets = self.env['mission.budget'].sudo().search([])
        # for budget in budgets:
        return budgets[-1].name

    def get_month_start(self):
        # Votre logique pour récupérer le 1er du mois
        # Par exemple:
        today = fields.Date.today()
        return today.replace(day=1)

    # Exemple de méthode existante qui renvoie la fin du mois
    def get_month_end(self):
        # Votre logique pour récupérer le dernier jour du mois
        # Par exemple:
        from calendar import monthrange
        today = fields.Date.today()
        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=last_day)


