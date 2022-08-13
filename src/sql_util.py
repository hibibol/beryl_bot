import sqlite3

from setting import DB_NAME

REGISTER_CHANNELDATA_SQL = """insert into ChannelData values (
:guild_id,
:category_id,
:boss1_channel_id,
:boss2_channel_id,
:boss3_channel_id,
:boss4_channel_id,
:boss5_channel_id
)"""
REGISTER_VIDEODATA_SQL = """insert into VideoData values (
:boss_name,
:video_id
)"""
DELETE_CHANNELDATA_SQL = """DELETE FROM ChannelData
where
    category_id=?
"""


def register_channel_data(params: tuple[int, ...]):
    con = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute(REGISTER_CHANNELDATA_SQL, params)
    con.commit()
    con.close()


def get_all_channel_data() -> list[tuple[int, int, tuple[int, int, int, int, int]]]:
    con = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    result = [(row[0], row[1], (*row[2:],)) for row in cur.execute("select * from ChannelData")]
    con.close()
    return result


def delete_channel_data(category_id: int):
    con = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute(DELETE_CHANNELDATA_SQL, (category_id,))
    con.commit()
    con.close()


def register_video_data(params: tuple[str, str]):
    con = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    cur.execute(REGISTER_VIDEODATA_SQL, params)
    con.commit()
    con.close()


def get_old_video_data(boss_name: str) -> list[str]:
    con = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cur = con.cursor()
    result = [row[0] for row in cur.execute("select videoid from VideoData where boss_name=?", (boss_name,))]
    con.close()
    return result
