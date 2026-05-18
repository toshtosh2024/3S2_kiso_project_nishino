from otree.api import *

class C(BaseConstants):
    NAME_IN_URL = 'school_choice_da'
    PLAYERS_PER_GROUP = 12
    NUM_ROUNDS = 5
    
    # --- ここが定数の定義 ---
    SCHOOLS = ['A', 'B', 'C', 'D']
    CAPACITY = 3  # 各学校の定員数。12人の学生を4校で分けるため各3名とする
    
    # 各学校の優先順位（1〜12の学生IDを並べたもの）
    # に基づき、学校側は優先順序（選好）を持つ
    # 【実験の仕掛け】
    # 学校Aはグループ2(4, 5, 6)を最優先します。
    # 学校Bはグループ1(1, 2, 3)を、グループ3(7, 8, 9)よりも優先します。
    # この設定によって、IA方式ではG1がA校に落ちてB校に行こうとした際、すでにG3でB校の定員が埋まっているという状況が発生し、
    # 一方DA方式では、B校に後から申し込んだG1が、優先順位の力でG3を弾き出す（仮受入の入れ替え）という結果の違いを生み出します。
    SCHOOL_PRIORITIES = {
        'A': [4, 5, 6, 1, 2, 3, 7, 8, 9, 10, 11, 12],
        'B': [1, 2, 3, 7, 8, 9, 4, 5, 6, 10, 11, 12],
        'C': [7, 8, 9, 4, 5, 6, 1, 2, 3, 10, 11, 12],
        'D': [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    }

    # 学生（1〜12のID）ごとの利得設定（選好順序）
    STUDENT_PAYOFFS = {
        # グループ1：第1希望A、第2希望B。Aの優先順位でG2に負けるためIAでは不利になるグループ。
        1: {'A': 100, 'B': 80, 'C': 60, 'D': 40},
        2: {'A': 100, 'B': 80, 'C': 60, 'D': 40},
        3: {'A': 100, 'B': 80, 'C': 60, 'D': 40},
        # グループ2：第1希望A。学校Aの優先順位が高いため、A校の席を確実に確保できるグループ。
        4: {'A': 100, 'C': 80, 'B': 60, 'D': 40},
        5: {'A': 100, 'C': 80, 'B': 60, 'D': 40},
        6: {'A': 100, 'C': 80, 'B': 60, 'D': 40},
        # グループ3：第1希望B。B校の優先順位はG1より低いが、IA方式では第1希望で申し込むことで席を先取りできるグループ。
        7: {'B': 100, 'A': 80, 'C': 60, 'D': 40},
        8: {'B': 100, 'A': 80, 'C': 60, 'D': 40},
        9: {'B': 100, 'A': 80, 'C': 60, 'D': 40},
        # グループ4：競合しないDへ向かう
        10: {'D': 100, 'C': 80, 'B': 60, 'A': 40},
        11: {'D': 100, 'C': 80, 'B': 60, 'A': 40},
        12: {'D': 100, 'C': 80, 'B': 60, 'A': 40},
    }

class Subsession(BaseSubsession):
    # DAまたはIAのどちらを実行するかを管理
    algorithm_type = models.StringField()

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # 学生が入力する希望順位
    rank1 = models.StringField(choices=C.SCHOOLS, label="第1希望")
    rank2 = models.StringField(choices=C.SCHOOLS, label="第2希望")
    rank3 = models.StringField(choices=C.SCHOOLS, label="第3希望")
    rank4 = models.StringField(choices=C.SCHOOLS, label="第4希望")
    
    # マッチング結果
    matched_school = models.StringField()
    payoff_rank = models.IntegerField() # 何番目の希望にマッチしたか


def creating_session(subsession: Subsession):
    # セッションの設定（settings.py）からアルゴリズム名を取得する
    # 設定がない場合のデフォルトは 'DA' にする
    subsession.algorithm_type = subsession.session.config.get('algorithm', 'DA')
    
    # ラウンドごとにプレイヤーの役割(id_in_group)をランダムにシャッフルする
    subsession.group_randomly()


# DA (Deferred Acceptance / ゲール・シャプレーアルゴリズム)
# 学生が希望順に申し込みを行い、学校側は定員内で優先順位の高い学生を「仮受け入れ (Deferred)」します。
# より優先順位の高い学生が後から来た場合、仮受け入れ中の学生を「突き放す (Reject)」ことで、最終的に安定なマッチングを実現します。
# この方式では、学生が自身の真の希望順位をそのまま申告することが最適な戦略(耐戦略性)となります。
def run_da_algorithm(group: Group):
    players = group.get_players()
    # 各学生の希望リスト（提出されたランキング）を作成
    student_prefs = {p.id_in_group: [p.rank1, p.rank2, p.rank3, p.rank4] for p in players}
    
    school_matches = {s: [] for s in C.SCHOOLS}
    unmatched_students = [p.id_in_group for p in players]
    student_proposals_count = {p.id_in_group: 0 for p in players} # 何番目の希望まで出したか

    while unmatched_students:
        s_id = unmatched_students.pop(0) # マッチしていない学生を1人取り出す
        # 次の希望校へ申し込む
        idx = student_proposals_count.get(s_id, 0)
        if idx >= len(C.SCHOOLS): continue # 全ての学校に断られた場合は終了
        
        target_school = student_prefs[s_id][idx]
        student_proposals_count[s_id] += 1 # 申し込み回数をカウントアップ
        
        # 学校側が申し込みを受け取り、仮受入リストに追加
        school_matches[target_school].append(s_id)
        # 仮受入リストを、その学校の優先順位リストに従ってソート（優先度の高い順）
        priority = C.SCHOOL_PRIORITIES[target_school]
        school_matches[target_school].sort(key=lambda x: priority.index(x))
        
        # 定員を超えた場合、一番優先順位が低い学生を突き放し、再度未マッチリストに戻す
        if len(school_matches[target_school]) > C.CAPACITY:
            rejected = school_matches[target_school].pop()
            unmatched_students.append(rejected)

    # 結果をPlayerモデルに保存
    for p in players:
        p.payoff_rank = 0 # 初期値（マッチしなかった場合は0）
        p.payoff = 0 # 初期値

    for school, students in school_matches.items():
        for s_id in students:
            p = group.get_player_by_id(s_id)
            p.matched_school = school
            prefs = [p.rank1, p.rank2, p.rank3, p.rank4]
            p.payoff_rank = prefs.index(school) + 1
            p.payoff = C.STUDENT_PAYOFFS[p.id_in_group][school]


# IA (Immediate Acceptance / ボストン方式)
# 学生の第1希望から順に、定員に達するまで「即時受け入れ (Immediate)」を確定させる方式です。
# 一度受け入れが確定すると、後から優先順位の高い学生が来ても覆りません。
# そのため、第1希望で競合に敗れると、第2希望の学校がすでに他の学生によって埋まってしまうリスクがあります。
# この方式では、学生が競合を避けて安全校を第1希望にする「戦略的な虚偽申告」を行うインセンティブが生じます。
def run_ia_algorithm(group: Group):
    players = group.get_players()
    remaining_students = [p.id_in_group for p in players]
    school_capacities = {s: C.CAPACITY for s in C.SCHOOLS}
    school_matches = {s: [] for s in C.SCHOOLS}

    for step in range(1, 5): # 第1希望から第4希望まで
        if not remaining_students: break
        
        proposals = {s: [] for s in C.SCHOOLS}
        for s_id in remaining_students:
            p = group.get_player_by_id(s_id)
            # stepに応じた希望校を取得
            target = [p.rank1, p.rank2, p.rank3, p.rank4][step-1]
            proposals[target].append(s_id)
            
        for school in C.SCHOOLS:
            if school_capacities[school] > 0 and proposals[school]:
                # 申し込んできた学生を学校の優先順位に従ってソート
                priority = C.SCHOOL_PRIORITIES[school]
                proposals[school].sort(key=lambda x: priority.index(x))
                
                # 空き定員の数だけ学生を即時受け入れ（確定）
                accepted = proposals[school][:school_capacities[school]]
                school_matches[school].extend(accepted)
                school_capacities[school] -= len(accepted)
                
                for s_id in accepted: # 受入が決まった学生を未マッチリストから除外
                    remaining_students.remove(s_id)
    
    # 結果保存 (DAと同様)
    for p in players:
        p.payoff_rank = 0 # 初期値
        p.payoff = 0 # 初期値

    for school, students in school_matches.items():
        for s_id in students:
            p = group.get_player_by_id(s_id)
            p.matched_school = school
            prefs = [p.rank1, p.rank2, p.rank3, p.rank4]
            p.payoff_rank = prefs.index(school) + 1
            p.payoff = C.STUDENT_PAYOFFS[p.id_in_group][school]

def run_matching_algorithm(group: Group):
    # 設定されたアルゴリズムに応じてマッチング処理を分岐
    if group.subsession.algorithm_type == 'IA':
        run_ia_algorithm(group)
    else:
        run_da_algorithm(group)

class Introduction(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return {
            'my_payoffs': C.STUDENT_PAYOFFS[player.id_in_group]
        }

class PreferenceSubmission(Page):
    form_model = 'player'
    form_fields = ['rank1', 'rank2', 'rank3', 'rank4']

    @staticmethod
    def error_message(player, values):
        ranks = [values['rank1'], values['rank2'], values['rank3'], values['rank4']]
        if len(set(ranks)) != len(ranks):
            return "同じ学校を複数選択することはできません。すべての希望順位に異なる学校を指定してください。"

class ResultsWaitPage(WaitPage):
    # 全員が入力し終えたら、GroupレベルでDA/IAアルゴリズムを実行する
    after_all_players_arrive = 'run_matching_algorithm' 
    title_text = "マッチング計算中"
    body_text = "他の参加者の入力が完了するまでお待ちください。"

class Results(Page):
    pass

page_sequence = [Introduction, PreferenceSubmission, ResultsWaitPage, Results]