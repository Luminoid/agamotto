# Seed list: what to include, which continuity it belongs to, and where it sits in the story.
# Everything factual that can be looked up (IDs, dates, zh titles, posters) comes from fetch.py.

# continuity id -> (franchise, en name, zh name, display order within franchise)
CONTINUITIES = {
    # Marvel
    "mcu":         ("marvel", "Marvel Cinematic Universe", "漫威电影宇宙", 1),
    "marvel-tv":   ("marvel", "Marvel Television (ABC, Hulu & Freeform)", "漫威电视剧（ABC、Hulu 与 Freeform）", 2),
    "ssu":         ("marvel", "Sony's Spider-Man Universe", "索尼蜘蛛侠宇宙", 3),
    "spiderverse": ("marvel", "Spider-Verse", "蜘蛛侠：纵横宇宙", 4),
    "raimi":       ("marvel", "Spider-Man (Raimi trilogy)", "蜘蛛侠（山姆·雷米三部曲）", 5),
    "webb":        ("marvel", "The Amazing Spider-Man", "超凡蜘蛛侠", 6),
    "blade":       ("marvel", "Blade trilogy", "刀锋战士三部曲", 7),
    "marvel-other":("marvel", "Other Marvel films & series", "其他漫威电影与剧集", 8),
    # X-Men
    "fox-xmen":    ("xmen", "X-Men film series (Fox)", "X战警电影系列（福克斯）", 1),
    "xmen-tas":    ("xmen", "X-Men: The Animated Series & '97", "X战警动画系列与《X战警97》", 2),
    "xmen-tv":     ("xmen", "Other X-Men series", "其他X战警剧集", 3),
    # DC
    "dcu":         ("dc", "DC Universe (2024–)", "DC宇宙（2024–）", 1),
    "dceu":        ("dc", "DC Extended Universe", "DC扩展宇宙", 2),
    "reeves":      ("dc", "The Batman saga (Reeves)", "新蝙蝠侠宇宙（里夫斯）", 3),
    "nolan":       ("dc", "The Dark Knight trilogy", "黑暗骑士三部曲", 4),
    "joker":       ("dc", "Joker films", "小丑系列", 5),
    "burton":      ("dc", "Batman (1989–1997)", "蝙蝠侠（1989–1997）", 6),
    "reeve":       ("dc", "Superman (1978–2006)", "超人（1978–2006）", 7),
    "arrowverse":  ("dc", "Arrowverse", "箭头宇宙", 8),
    "dcau":        ("dc", "DC Animated Universe", "DC动画宇宙", 9),
    "dc-tv":       ("dc", "Other DC series", "其他DC剧集", 10),
    "dc-other":    ("dc", "Other DC films", "其他DC电影", 11),
    # Star Wars
    "sw-canon":    ("starwars", "Star Wars canon", "星球大战正史", 1),
    "sw-legends":  ("starwars", "Legends & non-canon", "传说与非正史", 2),
    # Alien & Predator
    "alien":       ("alien", "Alien series", "异形系列", 1),
    "predator":    ("alien", "Predator series", "铁血战士系列", 2),
    "avp":         ("alien", "Alien vs. Predator", "异形大战铁血战士", 3),
    # Godzilla & MonsterVerse
    "monsterverse":("godzilla", "MonsterVerse (Legendary)", "怪兽宇宙（传奇影业）", 1),
    "gz-reiwa":    ("godzilla", "Toho Reiwa era (2016–)", "东宝令和系列（2016–）", 2),
    "gz-millennium":("godzilla", "Toho Millennium era (1999–2004)", "东宝千禧系列（1999–2004）", 3),
    "gz-heisei":   ("godzilla", "Toho Heisei era (1984–1995)", "东宝平成系列（1984–1995）", 4),
    "gz-showa":    ("godzilla", "Toho Shōwa era (1954–1975)", "东宝昭和系列（1954–1975）", 5),
    "gz-tristar":  ("godzilla", "TriStar Godzilla (1998–2000)", "美版哥斯拉（1998–2000）", 6),
    # Planet of the Apes
    "apes-reboot": ("apes", "Reboot series (2011–)", "猩球崛起系列（2011–）", 1),
    "apes-classic":("apes", "Original film series (1968–1973)", "原版电影系列（1968–1973）", 2),
    "apes-other":  ("apes", "Other versions", "其他版本", 3),
    # Dune
    "dune-legendary": ("dune", "Legendary's Dune (2021–)", "传奇影业《沙丘》（2021–）", 1),
    "dune-other":  ("dune", "Earlier adaptations", "早期改编", 2),
    # Middle-earth
    "me-jackson":  ("middleearth", "Peter Jackson's Middle-earth", "彼得·杰克逊的中土世界", 1),
    "me-rop":      ("middleearth", "The Rings of Power", "力量之戒", 2),
    "me-classic":  ("middleearth", "Animated adaptations (1977–1980)", "经典动画（1977–1980）", 3),
    # Wizarding World
    "ww-films":    ("wizarding", "Wizarding World films", "魔法世界电影", 1),
    "hp-hbo":      ("wizarding", "Harry Potter (HBO series)", "哈利·波特（HBO剧集）", 2),
    # Westeros
    "westeros":    ("westeros", "Game of Thrones universe", "权力的游戏宇宙", 1),
}

TITLES = []


def T(key, wiki, kind, cont, chrono, set_en="", set_zh=None, anim=False, also=None, qid=None, en=None, season=None):
    """kind: movie | series | special. chrono orders the story timeline inside a continuity."""
    # placement: (continuity, chrono, setting en, setting zh, season or None)
    places = [(cont, chrono, set_en, set_en if set_zh is None else set_zh, season)]
    for a in also or []:
        c, ch, se = a[:3]
        places.append((c, ch, se, a[3] if len(a) > 3 else se, a[4] if len(a) > 4 else None))
    # qid/en override for titles Wikipedia folds into a shared article (the article's poster is then skipped)
    TITLES.append(dict(key=key, wiki=wiki, kind=kind, anim=anim, places=places, qid=qid, en=en))


def sw(en):
    """Galactic years: '32 BBY' -> '雅汶前32年', 'c. 9 ABY' -> '约雅汶后9年'."""
    s = en.replace("c. ", "约")
    for era, zh in (("BBY", "雅汶前"), ("ABY", "雅汶后")):
        if s.endswith(" " + era):
            num = s[: -len(era) - 1]
            approx = num.startswith("约")
            num = num.lstrip("约")
            return ("约" if approx else "") + zh + num + "年"
    return s


MULTI = ("Multiverse", "多元宇宙")

# ---------------------------------------------------------------- Marvel Cinematic Universe
T("eyes-of-wakanda", "Eyes of Wakanda", "series", "mcu", 5, "1260 BC–1896", "公元前1260年–1896年", anim=True)
T("captain-america-tfa", "Captain America: The First Avenger", "movie", "mcu", 10, "1943–1945")
T("captain-marvel", "Captain Marvel (film)", "movie", "mcu", 20, "1995")
T("iron-man", "Iron Man (2008 film)", "movie", "mcu", 30, "2010")
T("iron-man-2", "Iron Man 2", "movie", "mcu", 40, "2011")
T("incredible-hulk", "The Incredible Hulk (film)", "movie", "mcu", 50, "2011")
T("thor", "Thor (film)", "movie", "mcu", 60, "2011")
T("avengers", "The Avengers (2012 film)", "movie", "mcu", 70, "2012")
T("iron-man-3", "Iron Man 3", "movie", "mcu", 80, "2012")
T("thor-dark-world", "Thor: The Dark World", "movie", "mcu", 90, "2013")
T("winter-soldier", "Captain America: The Winter Soldier", "movie", "mcu", 100, "2014")
T("gotg", "Guardians of the Galaxy (film)", "movie", "mcu", 110, "2014")
T("gotg-2", "Guardians of the Galaxy Vol. 2", "movie", "mcu", 120, "2014")
T("age-of-ultron", "Avengers: Age of Ultron", "movie", "mcu", 130, "2015")
T("ant-man", "Ant-Man (film)", "movie", "mcu", 140, "2015")
T("civil-war", "Captain America: Civil War", "movie", "mcu", 150, "2016")
T("black-widow", "Black Widow (2021 film)", "movie", "mcu", 160, "2016")
T("black-panther", "Black Panther (film)", "movie", "mcu", 170, "2016")
T("homecoming", "Spider-Man: Homecoming", "movie", "mcu", 180, "2016")
T("doctor-strange", "Doctor Strange (2016 film)", "movie", "mcu", 190, "2016–2017")
T("ragnarok", "Thor: Ragnarok", "movie", "mcu", 200, "2017")
T("ant-man-wasp", "Ant-Man and the Wasp", "movie", "mcu", 210, "2018")
T("infinity-war", "Avengers: Infinity War", "movie", "mcu", 220, "2018")
T("endgame", "Avengers: Endgame", "movie", "mcu", 230, "2018–2023")
T("loki", "Loki (TV series)", "series", "mcu", 240, "Outside time", "时间之外")
T("what-if", "What If...? (TV series)", "series", "mcu", 250, *MULTI, anim=True)
T("marvel-zombies", "Marvel Zombies (TV series)", "series", "mcu", 255, *MULTI, anim=True)
T("fns-spider-man", "Your Friendly Neighborhood Spider-Man", "series", "marvel-other", 2025, "Alternate universe", "平行宇宙", anim=True)
T("wandavision", "WandaVision", "series", "mcu", 260, "2023")
T("falcon-winter-soldier", "The Falcon and the Winter Soldier", "series", "mcu", 270, "2024")
T("shang-chi", "Shang-Chi and the Legend of the Ten Rings", "movie", "mcu", 280, "2024")
T("eternals", "Eternals (film)", "movie", "mcu", 290, "2024")
T("far-from-home", "Spider-Man: Far From Home", "movie", "mcu", 300, "2024")
T("no-way-home", "Spider-Man: No Way Home", "movie", "mcu", 310, "2024")
T("multiverse-of-madness", "Doctor Strange in the Multiverse of Madness", "movie", "mcu", 320)
T("hawkeye", "Hawkeye (2021 TV series)", "series", "mcu", 330, "2024")
T("moon-knight", "Moon Knight (TV series)", "series", "mcu", 340)
T("wakanda-forever", "Black Panther: Wakanda Forever", "movie", "mcu", 350)
T("echo", "Echo (TV series)", "series", "mcu", 360, "2025")
T("she-hulk", "She-Hulk: Attorney at Law", "series", "mcu", 370)
T("ms-marvel", "Ms. Marvel (TV series)", "series", "mcu", 380)
T("love-and-thunder", "Thor: Love and Thunder", "movie", "mcu", 390)
T("werewolf-by-night", "Werewolf by Night (film)", "special", "mcu", 400)
T("gotg-holiday", "The Guardians of the Galaxy Holiday Special", "special", "mcu", 410)
T("quantumania", "Ant-Man and the Wasp: Quantumania", "movie", "mcu", 420)
T("gotg-3", "Guardians of the Galaxy Vol. 3", "movie", "mcu", 430)
T("secret-invasion", "Secret Invasion (TV series)", "series", "mcu", 440)
T("the-marvels", "The Marvels", "movie", "mcu", 450)
T("deadpool-wolverine", "Deadpool & Wolverine", "movie", "mcu", 460, "Earth-10005", "地球-10005",
  also=[("fox-xmen", 200, "Earth-10005", "地球-10005")])
T("agatha", "Agatha All Along", "series", "mcu", 470)
T("born-again", "Daredevil: Born Again", "series", "mcu", 480)
T("ironheart", "Ironheart (TV series)", "series", "mcu", 490)
T("brave-new-world", "Captain America: Brave New World", "movie", "mcu", 500)
T("thunderbolts", "Thunderbolts*", "movie", "mcu", 510)
T("wonder-man", "Wonder Man (TV series)", "series", "mcu", 520)
T("punisher-one-last-kill", "The Punisher: One Last Kill", "special", "mcu", 530)
T("fantastic-four-first-steps", "The Fantastic Four: First Steps", "movie", "mcu", 540, "Earth-828", "地球-828")
T("brand-new-day", "Spider-Man: Brand New Day", "movie", "mcu", 550)
T("visionquest", "VisionQuest", "series", "mcu", 560)
T("avengers-doomsday", "Avengers: Doomsday", "movie", "mcu", 570)

# ---------------------------------------------------------------- Marvel Television
T("agent-carter", "Agent Carter (TV series)", "series", "marvel-tv", 1946, "1946")
T("agents-of-shield", "Agents of S.H.I.E.L.D.", "series", "marvel-tv", 2013, "2013–2019")
T("daredevil-netflix", "Daredevil (TV series)", "series", "mcu", 0)
T("jessica-jones", "Jessica Jones (TV series)", "series", "mcu", 0)
T("luke-cage", "Luke Cage (TV series)", "series", "mcu", 0)
T("iron-fist", "Iron Fist (TV series)", "series", "mcu", 0)
T("defenders", "The Defenders (miniseries)", "series", "mcu", 0)
T("punisher-netflix", "The Punisher (TV series)", "series", "mcu", 0)
T("inhumans", "Inhumans (TV series)", "series", "marvel-tv", 2017.4, "2017")
T("runaways", "Runaways (TV series)", "series", "marvel-tv", 2017.5, "2017")
T("cloak-dagger", "Cloak & Dagger (TV series)", "series", "marvel-tv", 2018, "2018")
T("helstrom", "Helstrom (TV series)", "series", "marvel-tv", 2020, "2020")

# ---------------------------------------------------------------- Sony's Spider-Man Universe
T("madame-web", "Madame Web (film)", "movie", "ssu", 10, "2003")
T("venom", "Venom (2018 film)", "movie", "ssu", 20)
T("venom-carnage", "Venom: Let There Be Carnage", "movie", "ssu", 30)
T("morbius", "Morbius (film)", "movie", "ssu", 40)
T("venom-last-dance", "Venom: The Last Dance", "movie", "ssu", 50)
T("kraven", "Kraven the Hunter (film)", "movie", "ssu", 60)

T("into-spider-verse", "Spider-Man: Into the Spider-Verse", "movie", "spiderverse", 10, anim=True)
T("across-spider-verse", "Spider-Man: Across the Spider-Verse", "movie", "spiderverse", 20, anim=True)

T("spider-man-2002", "Spider-Man (2002 film)", "movie", "raimi", 10)
T("spider-man-2", "Spider-Man 2", "movie", "raimi", 20)
T("spider-man-3", "Spider-Man 3", "movie", "raimi", 30)
T("amazing-spider-man", "The Amazing Spider-Man (film)", "movie", "webb", 10)
T("amazing-spider-man-2", "The Amazing Spider-Man 2", "movie", "webb", 20)

T("blade", "Blade (1998 film)", "movie", "blade", 10)
T("blade-2", "Blade II", "movie", "blade", 20)
T("blade-trinity", "Blade: Trinity", "movie", "blade", 30)

# Standalone: ordered by the year each story is set in
T("spider-noir", "Spider-Noir (TV series)", "series", "marvel-other", 1933, "1930s", "1930年代")
T("daredevil-2003", "Daredevil (2003 film)", "movie", "marvel-other", 2003.1, "2003")
T("hulk-2003", "Hulk (film)", "movie", "marvel-other", 2003.2, "2003")
T("punisher-2004", "The Punisher (2004 film)", "movie", "marvel-other", 2004, "2004")
T("elektra", "Elektra (2005 film)", "movie", "marvel-other", 2005.1, "2005")
T("fantastic-four-2005", "Fantastic Four (2005 film)", "movie", "marvel-other", 2005.2, "2005")
T("ghost-rider", "Ghost Rider (2007 film)", "movie", "marvel-other", 2007.1, "2007")
T("silver-surfer", "Fantastic Four: Rise of the Silver Surfer", "movie", "marvel-other", 2007.2, "2007")
T("punisher-war-zone", "Punisher: War Zone", "movie", "marvel-other", 2008, "2008")
T("ghost-rider-2", "Ghost Rider: Spirit of Vengeance", "movie", "marvel-other", 2011, "2011")
T("fantastic-four-2015", "Fantastic Four (2015 film)", "movie", "marvel-other", 2015, "2015")

# ---------------------------------------------------------------- X-Men
T("first-class", "X-Men: First Class", "movie", "fox-xmen", 10, "1962")
T("days-of-future-past", "X-Men: Days of Future Past", "movie", "fox-xmen", 20, "1973 & 2023", "1973年与2023年")
T("origins-wolverine", "X-Men Origins: Wolverine", "movie", "fox-xmen", 30, "1845–1979", "1845年–1979年")
T("apocalypse", "X-Men: Apocalypse", "movie", "fox-xmen", 40, "1983")
T("dark-phoenix", "Dark Phoenix (film)", "movie", "fox-xmen", 50, "1992")
T("new-mutants", "The New Mutants (film)", "movie", "fox-xmen", 60)
T("x-men-2000", "X-Men (film)", "movie", "fox-xmen", 70, "Near future", "近未来")
T("x2", "X2 (film)", "movie", "fox-xmen", 80)
T("last-stand", "X-Men: The Last Stand", "movie", "fox-xmen", 90)
T("the-wolverine", "The Wolverine (film)", "movie", "fox-xmen", 100)
T("deadpool", "Deadpool (film)", "movie", "fox-xmen", 110)
T("deadpool-2", "Deadpool 2", "movie", "fox-xmen", 120)
T("logan", "Logan (film)", "movie", "fox-xmen", 130, "2029")

T("x-men-tas", "X-Men: The Animated Series", "series", "xmen-tas", 10, "1992–1997", "1992年–1997年", anim=True)
T("x-men-97", "X-Men '97", "series", "xmen-tas", 20, "1997", anim=True)

T("x-men-evolution", "X-Men: Evolution", "series", "xmen-tv", 2000, "2000", anim=True)
T("wolverine-x-men", "Wolverine and the X-Men (TV series)", "series", "xmen-tv", 2009, "2009", anim=True)
T("legion", "Legion (TV series)", "series", "xmen-tv", 2017.1, "2017")
T("the-gifted", "The Gifted (American TV series)", "series", "xmen-tv", 2017.2, "2017")

# ---------------------------------------------------------------- DC Universe (Gunn & Safran)
T("creature-commandos", "Creature Commandos (TV series)", "series", "dcu", 10, anim=True)
T("superman-2025", "Superman (2025 film)", "movie", "dcu", 20)
# Peacemaker season 1 is DCEU (follows The Suicide Squad); season 2 is DCU (follows Superman)
T("peacemaker", "Peacemaker (TV series)", "series", "dcu", 30, season=2, also=[("dceu", 105, "", "", 1)])
T("supergirl-2026", "Supergirl (2026 film)", "movie", "dcu", 40)
T("lanterns", "Lanterns (TV series)", "series", "dcu", 50)
T("clayface", "Clayface (film)", "movie", "dcu", 60)

# ---------------------------------------------------------------- DC Extended Universe
T("wonder-woman", "Wonder Woman (2017 film)", "movie", "dceu", 10, "1918")
T("ww84", "Wonder Woman 1984", "movie", "dceu", 20, "1984")
T("man-of-steel", "Man of Steel (film)", "movie", "dceu", 30, "2013")
T("bvs", "Batman v Superman: Dawn of Justice", "movie", "dceu", 40, "2015")
T("suicide-squad", "Suicide Squad (2016 film)", "movie", "dceu", 50, "2016")
T("justice-league", "Justice League (film)", "movie", "dceu", 60, "2017")
T("snyder-cut", "Zack Snyder's Justice League", "movie", "dceu", 61, "2017")
T("aquaman", "Aquaman (film)", "movie", "dceu", 70)
T("shazam", "Shazam! (film)", "movie", "dceu", 80)
T("birds-of-prey", "Birds of Prey (2020 film)", "movie", "dceu", 90)
T("the-suicide-squad", "The Suicide Squad (film)", "movie", "dceu", 100)
T("black-adam", "Black Adam (film)", "movie", "dceu", 110)
T("shazam-2", "Shazam! Fury of the Gods", "movie", "dceu", 120)
T("the-flash", "The Flash (film)", "movie", "dceu", 130)
T("blue-beetle", "Blue Beetle (film)", "movie", "dceu", 140)
T("aquaman-2", "Aquaman and the Lost Kingdom", "movie", "dceu", 150)

T("the-batman", "The Batman (film)", "movie", "reeves", 10)
T("the-penguin", "The Penguin (TV series)", "series", "reeves", 20)

T("batman-begins", "Batman Begins", "movie", "nolan", 10)
T("dark-knight", "The Dark Knight", "movie", "nolan", 20)
T("dark-knight-rises", "The Dark Knight Rises", "movie", "nolan", 30)

T("joker", "Joker (2019 film)", "movie", "joker", 10, "1981")
T("joker-2", "Joker: Folie à Deux", "movie", "joker", 20, "1983")

T("batman-1989", "Batman (1989 film)", "movie", "burton", 10)
T("batman-returns", "Batman Returns", "movie", "burton", 20)
T("batman-forever", "Batman Forever", "movie", "burton", 30)
T("batman-robin", "Batman & Robin (film)", "movie", "burton", 40)

T("superman-1978", "Superman (1978 film)", "movie", "reeve", 10)
T("superman-2", "Superman II", "movie", "reeve", 20)
T("superman-3", "Superman III", "movie", "reeve", 30)
T("supergirl-1984", "Supergirl (1984 film)", "movie", "reeve", 40)
T("superman-4", "Superman IV: The Quest for Peace", "movie", "reeve", 50)
T("superman-returns", "Superman Returns", "movie", "reeve", 60)

T("arrow", "Arrow (TV series)", "series", "arrowverse", 10, "2012–2020", "2012年–2020年")
T("flash-2014", "The Flash (2014 TV series)", "series", "arrowverse", 20, "2014–2023", "2014年–2023年")
T("supergirl-tv", "Supergirl (TV series)", "series", "arrowverse", 30, "Earth-38", "地球-38")
T("legends", "Legends of Tomorrow", "series", "arrowverse", 40, "Across time", "穿越时空")
T("black-lightning", "Black Lightning (TV series)", "series", "arrowverse", 50)
T("batwoman", "Batwoman (TV series)", "series", "arrowverse", 60)
T("superman-lois", "Superman & Lois", "series", "arrowverse", 70)

T("btas", "Batman: The Animated Series", "series", "dcau", 10, anim=True)
T("mask-of-phantasm", "Batman: Mask of the Phantasm", "movie", "dcau", 20, anim=True)
T("stas", "Superman: The Animated Series", "series", "dcau", 30, anim=True)
T("justice-league-tas", "Justice League (TV series)", "series", "dcau", 40, anim=True)
T("jlu", "Justice League Unlimited", "series", "dcau", 50, anim=True)
T("batman-beyond", "Batman Beyond", "series", "dcau", 60, "2039", anim=True)

T("wonder-woman-tv", "Wonder Woman (TV series)", "series", "dc-tv", 1975, "1942 & 1977", "1942年与1977年")
T("lois-clark", "Lois & Clark: The New Adventures of Superman", "series", "dc-tv", 1993, "1993")
T("smallville", "Smallville", "series", "dc-tv", 2001, "2001")
T("gotham", "Gotham (TV series)", "series", "dc-tv", 2014, "2014")
T("lucifer", "Lucifer (TV series)", "series", "dc-tv", 2016, "2016")
T("titans", "Titans (2018 TV series)", "series", "dc-tv", 2018, "2018")
T("doom-patrol", "Doom Patrol (TV series)", "series", "dc-tv", 2019.1, "2019")
T("watchmen-tv", "Watchmen (TV series)", "series", "dc-tv", 2019.2, "2019")
T("harley-quinn", "Harley Quinn (TV series)", "series", "dc-tv", 2019.3, "2019", anim=True)
T("pennyworth", "Pennyworth (TV series)", "series", "dc-tv", 1960, "1960s", "1960年代")
T("stargirl", "Stargirl (TV series)", "series", "dc-tv", 2020, "2020")
T("sandman", "The Sandman (TV series)", "series", "dc-tv", 2022, "1916–2022", "1916年–2022年")
T("caped-crusader", "Batman: Caped Crusader", "series", "dc-tv", 1940, "1940s", "1940年代", anim=True)

T("batman-1966", "Batman (1966 film)", "movie", "dc-other", 1966, "1966")
T("watchmen", "Watchmen (2009 film)", "movie", "dc-other", 1985, "1985")
T("catwoman", "Catwoman (film)", "movie", "dc-other", 2004, "2004")
T("constantine", "Constantine (film)", "movie", "dc-other", 2005, "2005")
T("green-lantern", "Green Lantern (film)", "movie", "dc-other", 2011, "2011")
T("lego-batman", "The Lego Batman Movie", "movie", "dc-other", 2017, "2017", anim=True)
T("super-pets", "DC League of Super-Pets", "movie", "dc-other", 2022, "2022", anim=True)

# ---------------------------------------------------------------- Star Wars (chrono = galactic year, BBY negative)
TALES = "Star Wars Tales (TV anthology)"


def S(key, wiki, kind, year, label, anim=False, **kw):
    T(key, wiki, kind, "sw-canon", year, label, sw(label), anim=anim, **kw)

S("young-jedi", "Star Wars: Young Jedi Adventures", "series", -232, "c. 232 BBY", anim=True)
S("acolyte", "Star Wars: The Acolyte", "series", -132, "132 BBY")
S("tales-jedi", TALES, "series", -19.5, "36–18 BBY", anim=True, qid="Q112170063", en="Star Wars: Tales of the Jedi")
S("phantom-menace", "Star Wars: Episode I – The Phantom Menace", "movie", -32, "32 BBY")
S("attack-clones", "Star Wars: Episode II – Attack of the Clones", "movie", -22, "22 BBY")
S("clone-wars-film", "Star Wars: The Clone Wars (film)", "movie", -21.9, "22 BBY", anim=True)
S("clone-wars", "Star Wars: The Clone Wars (2008 TV series)", "series", -21.8, "22–19 BBY", anim=True)
S("revenge-sith", "Star Wars: Episode III – Revenge of the Sith", "movie", -19.1, "19 BBY")
S("tales-underworld", TALES, "series", -18.95, "c. 19 BBY", anim=True, qid="Q133810179", en="Star Wars: Tales of the Underworld")
S("tales-empire", TALES, "series", -18.98, "c. 19 BBY", anim=True, qid="Q125338461", en="Star Wars: Tales of the Empire")
S("bad-batch", "Star Wars: The Bad Batch", "series", -18.9, "19–18 BBY", anim=True)
S("maul-shadow-lord", "Star Wars: Maul – Shadow Lord", "series", -18, "c. 18 BBY", anim=True)
S("solo", "Solo: A Star Wars Story", "movie", -13, "13–10 BBY")
S("obi-wan", "Obi-Wan Kenobi (TV series)", "series", -9, "9 BBY")
S("andor", "Andor (TV series)", "series", -5.1, "5–1 BBY")
S("rebels", "Star Wars Rebels", "series", -5, "5–0 BBY", anim=True)
S("rogue-one", "Rogue One", "movie", -0.1, "0 BBY")
S("new-hope", "Star Wars (film)", "movie", 0, "0 BBY")
S("empire", "The Empire Strikes Back", "movie", 3, "3 ABY")
S("jedi", "Return of the Jedi", "movie", 4, "4 ABY")
S("mandalorian", "The Mandalorian", "series", 9, "9 ABY")
S("boba-fett", "The Book of Boba Fett", "series", 9.1, "9 ABY")
S("skeleton-crew", "Star Wars: Skeleton Crew", "series", 9.2, "c. 9 ABY")
S("mando-grogu", "The Mandalorian and Grogu", "movie", 9.3, "c. 9 ABY")
S("ahsoka", "Ahsoka (TV series)", "series", 9.15, "c. 9–11 ABY")
S("resistance", "Star Wars Resistance", "series", 33.9, "34 ABY", anim=True)
S("force-awakens", "Star Wars: The Force Awakens", "movie", 34, "34 ABY")
S("last-jedi", "Star Wars: The Last Jedi", "movie", 34.1, "34 ABY")
S("rise-skywalker", "Star Wars: The Rise of Skywalker", "movie", 35, "35 ABY")

T("clone-wars-2003", "Star Wars: Clone Wars (2003 TV series)", "series", "sw-legends", 10, "Legends", "传说", anim=True)
T("visions", "Star Wars: Visions", "series", "sw-legends", 20, "Non-canon", "非正史", anim=True)


# ---------------------------------------------------------------- franchises added in v4
def SEQ(cont, items):
    """Story order is list order: (key, wiki, kind, setting en, setting zh or None, animated)."""
    for i, it in enumerate(items):
        key, wiki, kind = it[:3]
        T(key, wiki, kind, cont, (i + 1) * 10, it[3] if len(it) > 3 else "", it[4] if len(it) > 4 else None,
          anim=it[5] if len(it) > 5 else False)


FUTURE = ("Future", "未来")
FAR = ("Far future", "遥远未来")

# Alien & Predator: in-film years
SEQ("alien", [
    ("prometheus", "Prometheus (2012 film)", "movie", "2093"),
    ("covenant", "Alien: Covenant", "movie", "2104"),
    ("alien-earth", "Alien: Earth", "series", "2120"),
    ("alien-1979", "Alien (film)", "movie", "2122"),
    ("romulus", "Alien: Romulus", "movie", "2142"),
    ("aliens", "Aliens (film)", "movie", "2179"),
    ("alien-3", "Alien 3", "movie", "2179"),
    ("alien-resurrection", "Alien Resurrection", "movie", "2379"),
])
SEQ("predator", [
    ("killer-of-killers", "Predator: Killer of Killers", "movie", "841–1942", None, True),
    ("prey", "Prey (2022 film)", "movie", "1719"),
    ("predator-1987", "Predator (film)", "movie", "1987"),
    ("predator-2", "Predator 2", "movie", "1997"),
    ("predators", "Predators (2010 film)", "movie", "2010"),
    ("the-predator", "The Predator (film)", "movie", "2018"),
    ("badlands", "Predator: Badlands", "movie", *FUTURE),
])
SEQ("avp", [
    ("avp", "Alien vs. Predator (film)", "movie", "2004"),
    ("avp-requiem", "Aliens vs. Predator: Requiem", "movie", "2004"),
])

# Godzilla: MonsterVerse by in-universe year; Toho eras are separate continuities
SEQ("monsterverse", [
    ("kong-skull-island", "Kong: Skull Island", "movie", "1973"),
    ("skull-island-tv", "Skull Island (TV series)", "series", "1993", None, True),
    ("godzilla-2014", "Godzilla (2014 film)", "movie", "2014"),
    ("monarch", "Monarch: Legacy of Monsters", "series", "1950s & 2015", "1950年代与2015年"),
    ("kotm", "Godzilla: King of the Monsters (2019 film)", "movie", "2019"),
    ("gvk", "Godzilla vs. Kong", "movie", "2024"),
    ("gxk", "Godzilla x Kong: The New Empire", "movie", "2027"),
])
# standalone stories, ordered by when each is set
SEQ("gz-reiwa", [
    ("minus-one", "Godzilla Minus One", "movie", "1945–1947"),
    ("minus-zero", "Godzilla Minus Zero", "movie", "After 1947", "1947年后"),
    ("shin-godzilla", "Shin Godzilla", "movie", "Present day", "当代"),
    ("singular-point", "Godzilla Singular Point", "series", "2030", None, True),
    ("planet-of-monsters", "Godzilla: Planet of the Monsters", "movie", *FAR, True),
    ("city-edge-battle", "Godzilla: City on the Edge of Battle", "movie", *FAR, True),
    ("planet-eater", "Godzilla: The Planet Eater", "movie", *FAR, True),
])
# each a sequel to the 1954 film only, so release order
SEQ("gz-millennium", [
    ("godzilla-2000", "Godzilla 2000", "movie"),
    ("megaguirus", "Godzilla vs. Megaguirus", "movie"),
    ("gmk", "Godzilla, Mothra and King Ghidorah: Giant Monsters All-Out Attack", "movie"),
    ("against-mechagodzilla", "Godzilla Against Mechagodzilla", "movie"),
    ("tokyo-sos", "Godzilla: Tokyo S.O.S.", "movie"),
    ("final-wars", "Godzilla: Final Wars", "movie"),
])
SEQ("gz-heisei", [
    ("return-of-godzilla", "The Return of Godzilla", "movie", "1984"),
    ("biollante", "Godzilla vs. Biollante", "movie"),
    ("vs-king-ghidorah", "Godzilla vs. King Ghidorah", "movie"),
    ("vs-mothra", "Godzilla vs. Mothra", "movie"),
    ("mechagodzilla-ii", "Godzilla vs. Mechagodzilla II", "movie"),
    ("spacegodzilla", "Godzilla vs. SpaceGodzilla", "movie"),
    ("destoroyah", "Godzilla vs. Destoroyah", "movie"),
])
# Destroy All Monsters is set at the end of the 20th century, after the rest of the era
SEQ("gz-showa", [
    ("godzilla-1954", "Godzilla (1954 film)", "movie", "1954"),
    ("raids-again", "Godzilla Raids Again", "movie"),
    ("kong-vs-godzilla", "King Kong vs. Godzilla", "movie"),
    ("mothra-vs-godzilla", "Mothra vs. Godzilla", "movie"),
    ("ghidorah", "Ghidorah, the Three-Headed Monster", "movie"),
    ("astro-monster", "Invasion of Astro-Monster", "movie"),
    ("ebirah", "Ebirah, Horror of the Deep", "movie"),
    ("son-of-godzilla", "Son of Godzilla", "movie"),
    ("all-monsters-attack", "All Monsters Attack", "movie"),
    ("hedorah", "Godzilla vs. Hedorah", "movie"),
    ("gigan", "Godzilla vs. Gigan", "movie"),
    ("megalon", "Godzilla vs. Megalon", "movie"),
    ("vs-mechagodzilla", "Godzilla vs. Mechagodzilla", "movie"),
    ("terror-mechagodzilla", "Terror of Mechagodzilla", "movie"),
    ("destroy-all-monsters", "Destroy All Monsters", "movie", "1999"),
])
SEQ("gz-tristar", [
    ("godzilla-1998", "Godzilla (1998 film)", "movie", "1998"),
    ("godzilla-the-series", "Godzilla: The Series", "series", "1998–2000", None, True),
])

# Planet of the Apes
SEQ("apes-reboot", [
    ("rise-apes", "Rise of the Planet of the Apes", "movie", "Present day", "当代"),
    ("dawn-apes", "Dawn of the Planet of the Apes", "movie", "10 years later", "十年后"),
    ("war-apes", "War for the Planet of the Apes", "movie", "12 years later", "十二年后"),
    ("kingdom-apes", "Kingdom of the Planet of the Apes", "movie", "Generations later", "数代之后"),
])
# Escape sends three apes back from 3978 to 1973, so the story years start there
SEQ("apes-classic", [
    ("escape-apes", "Escape from the Planet of the Apes", "movie", "1973"),
    ("conquest-apes", "Conquest of the Planet of the Apes", "movie", "1991"),
    ("battle-apes", "Battle for the Planet of the Apes", "movie", "Told in 2670", "2670年回述"),
    ("apes-1968", "Planet of the Apes (1968 film)", "movie", "3978"),
    ("beneath-apes", "Beneath the Planet of the Apes", "movie", "3978"),
])
SEQ("apes-other", [
    ("apes-tv-1974", "Planet of the Apes (TV series)", "series", "3085"),
    ("return-apes", "Return to the Planet of the Apes", "series", *FAR, True),
    ("apes-2001", "Planet of the Apes (2001 film)", "movie", "5021"),
])

# Dune
SEQ("dune-legendary", [
    ("dune-prophecy", "Dune: Prophecy", "series", "10,000 years earlier", "一万年前"),
    ("dune-2021", "Dune (2021 film)", "movie", "10191 AG", "公会纪元10191年"),
    ("dune-part-two", "Dune: Part Two", "movie", "10191 AG", "公会纪元10191年"),
    ("dune-part-three", "Dune: Part Three", "movie", "Nearly 20 years later", "近二十年后"),
])
SEQ("dune-other", [
    ("dune-1984", "Dune (1984 film)", "movie", "10191 AG", "公会纪元10191年"),
    ("dune-2000", "Frank Herbert's Dune", "series", "10191 AG", "公会纪元10191年"),
    ("children-of-dune", "Frank Herbert's Children of Dune", "series", "12–21 years later", "12–21年后"),
])

# Middle-earth: Tolkien's Third Age dates (Appendix B)
def TA(y):
    return (f"T.A. {y}", f"第三纪元{y}年")


SEQ("me-jackson", [
    ("rohirrim", "The Lord of the Rings: The War of the Rohirrim", "movie", *TA("2758–2759"), True),
    ("hobbit-1", "The Hobbit: An Unexpected Journey", "movie", *TA(2941)),
    ("hobbit-2", "The Hobbit: The Desolation of Smaug", "movie", *TA(2941)),
    ("hobbit-3", "The Hobbit: The Battle of the Five Armies", "movie", *TA(2941)),
    ("fellowship", "The Lord of the Rings: The Fellowship of the Ring", "movie", *TA("3001–3019")),
    ("two-towers", "The Lord of the Rings: The Two Towers", "movie", *TA(3019)),
    ("return-king", "The Lord of the Rings: The Return of the King", "movie", *TA("3019–3021")),
])
SEQ("me-rop", [
    ("rings-of-power", "The Lord of the Rings: The Rings of Power", "series", "Second Age", "第二纪元"),
])
SEQ("me-classic", [
    ("hobbit-1977", "The Hobbit (1977 film)", "movie", *TA(2941), True),
    ("lotr-1978", "The Lord of the Rings (1978 film)", "movie", *TA("3018–3019"), True),
    ("return-king-1980", "The Return of the King (1980 film)", "movie", *TA(3019), True),
])

# Wizarding World
SEQ("ww-films", [
    ("fantastic-beasts", "Fantastic Beasts and Where to Find Them (film)", "movie", "1926"),
    ("crimes-grindelwald", "Fantastic Beasts: The Crimes of Grindelwald", "movie", "1927"),
    ("secrets-dumbledore", "Fantastic Beasts: The Secrets of Dumbledore", "movie", "1930s", "1930年代"),
    ("hp-1", "Harry Potter and the Philosopher's Stone (film)", "movie", "1991–1992"),
    ("hp-2", "Harry Potter and the Chamber of Secrets (film)", "movie", "1992–1993"),
    ("hp-3", "Harry Potter and the Prisoner of Azkaban (film)", "movie", "1993–1994"),
    ("hp-4", "Harry Potter and the Goblet of Fire (film)", "movie", "1994–1995"),
    ("hp-5", "Harry Potter and the Order of the Phoenix (film)", "movie", "1995–1996"),
    ("hp-6", "Harry Potter and the Half-Blood Prince (film)", "movie", "1996–1997"),
    ("hp-7", "Harry Potter and the Deathly Hallows – Part 1", "movie", "1997–1998"),
    ("hp-8", "Harry Potter and the Deathly Hallows – Part 2", "movie", "1998"),
])
SEQ("hp-hbo", [
    ("hp-hbo", "Harry Potter (TV series)", "series", "1991–1992"),
])

# Westeros: years After the Conquest
SEQ("westeros", [
    ("house-of-the-dragon", "House of the Dragon", "series", "From 101 AC", "征服后101年起"),
    ("knight-seven-kingdoms", "A Knight of the Seven Kingdoms (TV series)", "series", "209 AC", "征服后209年"),
    ("game-of-thrones", "Game of Thrones", "series", "298–305 AC", "征服后298–305年"),
])


# ---------------------------------------------------------------- official MCU order
# Marvel's "Complete MCU Timeline" on Disney+ (marvel.com, 2026-06-02), seasons placed separately.
# Brand New Day, VisionQuest and Doomsday postdate that list and follow One Last Kill.
MCU_ORDER = [
    ("eyes-of-wakanda", None, "1260 BC–1896", "公元前1260年–1896年"),
    ("captain-america-tfa", None, "1943–1945"), ("captain-marvel", None, "1995"), ("iron-man", None, "2010"),
    ("iron-man-2", None, "2011"), ("incredible-hulk", None, "2011"), ("thor", None, "2011"),
    ("avengers", None, "2012"), ("thor-dark-world", None, "2013"), ("iron-man-3", None, "2012–2013"),
    ("winter-soldier", None, "2014"), ("gotg", None, "2014"), ("gotg-2", None, "2014"),
    ("daredevil-netflix", 1), ("jessica-jones", 1), ("age-of-ultron", None, "2015"), ("ant-man", None, "2015"),
    ("daredevil-netflix", 2), ("luke-cage", 1), ("iron-fist", 1), ("defenders", None),
    ("civil-war", None, "2016"), ("black-widow", None, "2016"), ("black-panther", None, "2016"),
    ("homecoming", None, "2016"), ("punisher-netflix", 1), ("doctor-strange", None, "2016–2017"),
    ("jessica-jones", 2), ("luke-cage", 2), ("iron-fist", 2), ("daredevil-netflix", 3),
    ("ragnarok", None, "2017"), ("punisher-netflix", 2), ("jessica-jones", 3),
    ("ant-man-wasp", None, "2018"), ("infinity-war", None, "2018"), ("endgame", None, "2018–2023"),
    ("loki", 1, "Outside time", "时间之外"), ("what-if", 1, *MULTI), ("marvel-zombies", None, *MULTI),
    ("wandavision", None, "2023"), ("shang-chi", None, "2024"), ("falcon-winter-soldier", None, "2024"),
    ("far-from-home", None, "2024"), ("eternals", None, "2024"), ("no-way-home", None, "2024"),
    ("multiverse-of-madness", None), ("hawkeye", None, "2024"), ("moon-knight", None),
    ("wakanda-forever", None), ("echo", None, "2025"), ("she-hulk", None), ("ms-marvel", None),
    ("love-and-thunder", None), ("ironheart", None), ("werewolf-by-night", None), ("gotg-holiday", None),
    ("quantumania", None), ("gotg-3", None), ("secret-invasion", None), ("the-marvels", None),
    ("loki", 2, "Outside time", "时间之外"), ("what-if", 2, *MULTI),
    ("deadpool-wolverine", None, "Earth-10005", "地球-10005"), ("agatha", None), ("what-if", 3, *MULTI),
    ("born-again", 1), ("brave-new-world", None), ("thunderbolts", None),
    ("fantastic-four-first-steps", None, "Earth-828", "地球-828"), ("wonder-man", None), ("born-again", 2),
    ("punisher-one-last-kill", None), ("brand-new-day", None), ("visionquest", None), ("avengers-doomsday", None),
]


def apply_order(cont, order):
    by_key = {t["key"]: t for t in TITLES}
    keys = {o[0] for o in order}
    missing = [t["key"] for t in TITLES if any(p[0] == cont for p in t["places"]) and t["key"] not in keys]
    assert not missing, f"{cont} titles missing from order: {missing}"
    for t in TITLES:
        if t["key"] in keys:
            t["places"] = [p for p in t["places"] if p[0] != cont]
    new = {}
    for i, o in enumerate(order):
        key, season = o[0], o[1]
        se = o[2] if len(o) > 2 else ""
        sz = o[3] if len(o) > 3 else se
        new.setdefault(key, []).append((cont, (i + 1) * 10, se, sz, season))
    for key, ps in new.items():
        by_key[key]["places"] = ps + by_key[key]["places"]


apply_order("mcu", MCU_ORDER)
