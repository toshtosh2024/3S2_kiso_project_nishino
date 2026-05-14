from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'my_public_goods'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 1
    ENDOWMENT = cu(1000)
    MULTIPLIER = 2

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    total_contribution = models.CurrencyField()
    individual_share = models.CurrencyField()

class Player(BasePlayer):
    contribution = models.CurrencyField(
        min=0,
        max=C.ENDOWMENT,
        label='公共財にいくら投資しますか？',
    )

def set_payoffs(group):
    players = group.get_players()
    contributions = [p.contribution for p in players]
    group.total_contribution = sum(contributions)
    group.individual_share = (
        group.total_contribution * C.MULTIPLIER /
C.PLAYERS_PER_GROUP
    )
    for player in players:
        player.payoff = C.ENDOWMENT - player.contribution +group.individual_share

class MyPage(Page):
    form_model = 'player'
    form_fields = ['contribution']

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'

class Results(Page):
    pass

page_sequence = [
    MyPage,
    ResultsWaitPage,
    Results
]