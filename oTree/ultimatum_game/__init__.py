from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'ultimatum_game'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    INITIAL_BUDGET = cu(1000)
    R = 0.8  # 割引因子

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    # 現在のラウンドでの予算を保持するフィールドを追加
    budget = models.CurrencyField()
    x = models.CurrencyField(
        label='自分の取り分として提案する額を入力してください',
        min=0,
    )
    agree = models.BooleanField(
        label='提案を受け入れますか？',
        choices=[[True, '受け入れる'], [False, '拒否する']],
        widget=widgets.RadioSelect,
    )

class Player(BasePlayer):
    pass

# --- 補助関数 ---
def get_budget(group: Group):
    # ラウンドごとの予算を計算
    return C.INITIAL_BUDGET * (C.R ** (group.round_number - 1))

def is_finished(group: Group):
    # 過去のラウンドで誰かが合意（agree == True）したかチェック
    prev_rounds = group.in_previous_rounds()
    return any(g.agree is True for g in prev_rounds)

def _proposer_id(round_number):
    return 1 if round_number % 2 == 1 else 2

def _receiver_id(round_number):
    return 2 if round_number % 2 == 1 else 1

# --- フィールドの動的バリデーション ---
def x_max(group: Group):
    return get_budget(group)

# --- ロジック ---
def creating_session(subsession: Subsession):
    for g in subsession.get_groups():
        g.budget = get_budget(g)

def set_payoffs(group: Group):
    # すでに終了している場合は何もしない
    if is_finished(group):
        return

    proposer = group.get_player_by_id(_proposer_id(group.round_number))
    receiver = group.get_player_by_id(_receiver_id(group.round_number))

    if group.agree:
        proposer.payoff = group.x
        receiver.payoff = group.budget - group.x
    else:
        # 拒否された場合、最終ラウンドなら全員0
        if group.round_number == C.NUM_ROUNDS:
            proposer.payoff = cu(0)
            receiver.payoff = cu(0)
        # 最終ラウンドでなければ、このラウンドの利得は0のまま次へ
        else:
            pass

# --- ページ定義 ---
class Proposer(Page):
    form_model = 'group'
    form_fields = ['x']

    @staticmethod
    def is_displayed(player: Player):
        group = player.group
        return not is_finished(group) and player.id_in_group == _proposer_id(group.round_number)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            budget=player.group.budget,
            round_number=player.round_number,
        )

class WaitForProposer(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return not is_finished(player.group)

class Receiver(Page):
    form_model = 'group'
    form_fields = ['agree']

    @staticmethod
    def is_displayed(player: Player):
        group = player.group
        return not is_finished(group) and player.id_in_group == _receiver_id(group.round_number)

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        return dict(
            budget=group.budget,
            x=group.x,
            receiver_share=group.budget - group.x,
            round_number=group.round_number,
        )

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'
    
    @staticmethod
    def is_displayed(player: Player):
        return not is_finished(player.group)

class Results(Page):
    # @staticmethod を削除
    def is_displayed(player: Player):
        return player.group.field_maybe_none('agree') is not None

    # @staticmethod を削除
    def vars_for_template(player: Player):
        group = player.group
        # player.round_number を直接利用する
        rn = player.round_number
        
        # 予算の計算
        current_budget = cu(float(C.INITIAL_BUDGET) * (C.R ** (rn - 1)))
        
        # 次のラウンドがある場合のみ予算を設定、ない場合は False を返す（HTMLでの判定を確実にするため）
        if rn < C.NUM_ROUNDS:
            next_budget = cu(float(C.INITIAL_BUDGET) * (C.R ** rn))
        else:
            next_budget = False
            
        return dict(
            agreed=group.agree,
            current_budget=current_budget,
            next_budget=next_budget,
            x=group.x,
            is_proposer=player.id_in_group == _proposer_id(rn)
        )

page_sequence = [Proposer, WaitForProposer, Receiver, ResultsWaitPage, Results]