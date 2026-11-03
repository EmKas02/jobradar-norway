from jobradar.matcher import Matcher

PROFILE = {
    "summary": "Junior data analyst with Python, SQL and Power BI.",
    "skills": {"python": ["python"], "sql": ["sql"], "power bi": ["power bi"]},
    "skill_target": 3,
}


def ad(title, text, remote=0):
    return {"title": title, "text": text, "remote": remote}


def test_junior_data_role_beats_senior_and_unrelated():
    junior = ad("Junior Data Analyst", "Nyutdannet? Du bruker Python, SQL og Power BI.")
    senior = ad("Senior Data Engineer", "Minst 7 års erfaring med Python og SQL.")
    chef = ad("Kokk", "Vi søker kokk til kjøkkenet.")
    m_junior, m_senior, m_chef = Matcher(PROFILE).score_many([junior, senior, chef])
    assert m_junior.score > m_senior.score > m_chef.score
    assert set(m_junior.skills) == {"python", "sql", "power bi"}
    assert "senior title" in m_senior.flags
    assert "asks 7+ yrs" in m_senior.flags


def test_skill_aliases_need_word_boundaries():
    m = Matcher(PROFILE).score_many([ad("Analyst", "We use sqlite and pythonic tools")])[0]
    assert m.skills == []


def test_academic_posts_are_penalised():
    phd = Matcher(PROFILE).score_many([ad("PhD Candidate in Data Science", "Python and SQL.")])[0]
    assert "academic post" in phd.flags


def test_ads_requiring_other_languages_are_penalised():
    profile = {**PROFILE, "languages": ["english", "norwegian", "polish"]}
    german = ad("Werkstudent Data Analyst (m/w/d)", "Fluent German required. Python, SQL.")
    polish = ad("Junior Data Analyst", "Fluent Polish is a plus. Python, SQL.")
    m_german, m_polish = Matcher(profile).score_many([german, polish])
    assert "needs other language" in m_german.flags
    assert "needs other language" not in m_polish.flags
    slavic = Matcher(profile).score_many([ad("Junior Analyst", "Language: English, Ukrainian or Russian (fluent)")])[0]
    assert "needs other language" in slavic.flags
