from odoo import fields, models, api


class Adresse(models.Model):
    _name = "mission.adresse"
    _description = "Adresse de déstination pour mission"

    nom_ville = fields.Char(string="Ville")
    #lieu_mission = fields.Char(string="Lieu de la mission")
    distance = fields.Integer(string="Distance par rapport à Dakar en KM")

    _sql_constraints = [
        ('nom_ville_uniq', 'unique (nom_ville)', 'Cette ville existe déjà')
    ]

    def name_get(self):
        ad = []
        for record in self:
            rec_name = "%s" % (record.nom_ville)
            ad.append((record.id, rec_name))
        return ad