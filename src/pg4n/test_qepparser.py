import pytest
import psycopg

from os import getenv
from pytest_postgresql import factories
from psycopg import Connection

from pg4n import qepparser


def load_database(**kwargs):
    conn: Connection = psycopg.connect(**kwargs)
    with conn.cursor() as cur:
        cur.execute("""
        -- for copy-and-pasting
        drop table if exists comments;
        drop table if exists users;
        drop table if exists stories;
        
        -- demonstrates relational data
        create table stories (id serial primary key, name varchar);
        create table users (id serial primary key, name varchar);
        create table comments (
            id serial primary key,
            story_id integer references stories(id) on delete cascade,
            user_id integer references users(id) on delete cascade,
            comment varchar);
            
        -- populate with sample data
        insert into stories (name) values ('story1');
        insert into stories (name) values ('story2');
        insert into users (name) values ('user1');
        insert into users (name) values ('user2');
        insert into comments (story_id, user_id, comment) values (1, 1, 'comment1');
        insert into comments (story_id, user_id, comment) values (1, 2, 'comment2');
        insert into comments (story_id, user_id, comment) values (2, 1, 'comment3');
        insert into comments (story_id, user_id, comment) values (2, 2, 'comment4');
        """)
        conn.commit()


postgresql_in_docker = factories.postgresql_noproc(
    load=[load_database],
    user=getenv("POSTGRES_USER", "postgres"),
    password=getenv("POSTGRES_PASSWORD", "postgres"))
postgresql = factories.postgresql("postgresql_in_docker")


@pytest.fixture
def parser(postgresql: Connection):
    return qepparser.QEPParser(conn=postgresql)


def test_qep_structure(parser: qepparser.QEPParser):
    """Test that the QEP structure is as expected."""

    qep = parser("select * from stories")
    assert qep.plan["Node Type"] == "Seq Scan"
    assert qep.plan["Relation Name"] == "stories"
    assert qep.plan["Alias"] == "stories"
    assert qep.plan["Actual Rows"] == 2

    qep = parser("select * from users")
    assert qep.plan["Node Type"] == "Seq Scan"
    assert qep.plan["Relation Name"] == "users"
    assert qep.plan["Alias"] == "users"
    assert qep.plan["Actual Rows"] == 2

    qep = parser("select * from comments")
    assert qep.plan["Node Type"] == "Seq Scan"
    assert qep.plan["Relation Name"] == "comments"
    assert qep.plan["Alias"] == "comments"
    assert qep.plan["Actual Rows"] == 4

    qep = parser("select * from stories where id = 1")
    assert qep.plan["Node Type"] == "Index Scan"
    assert qep.plan["Relation Name"] == "stories"
    assert qep.plan["Alias"] == "stories"
    assert qep.plan["Actual Rows"] == 1

    qep = parser("select * from users where id = 1")
    assert qep.plan["Node Type"] == "Index Scan"
    assert qep.plan["Relation Name"] == "users"
    assert qep.plan["Alias"] == "users"
    assert qep.plan["Actual Rows"] == 1

    qep = parser("select * from comments where id = 1")
    assert qep.plan["Node Type"] == "Index Scan"
    assert qep.plan["Relation Name"] == "comments"
    assert qep.plan["Alias"] == "comments"
    assert qep.plan["Actual Rows"] == 1

    qep = parser("select * from stories where id = 1 and id = 2")
    assert qep.plan["Node Type"] == "Result"
    assert qep.root[0].plan["Node Type"] == "Index Scan"
    assert qep.root[0].plan["Relation Name"] == "stories"
    assert qep.root[0].plan["Alias"] == "stories"
    assert qep.root[0].plan["Actual Rows"] == 0

    qep = parser("select * from users where id = 1 and id = 2")
    assert qep.plan["Node Type"] == "Result"
    assert qep.root[0].plan["Node Type"] == "Index Scan"
    assert qep.root[0].plan["Relation Name"] == "users"
    assert qep.root[0].plan["Alias"] == "users"
    assert qep.root[0].plan["Actual Rows"] == 0

    qep = parser("select * from comments where id = 1 and id = 2")
    assert qep.plan["Node Type"] == "Result"
    assert qep.root[0].plan["Node Type"] == "Index Scan"
    assert qep.root[0].plan["Relation Name"] == "comments"
    assert qep.root[0].plan["Alias"] == "comments"
    assert qep.root[0].plan["Actual Rows"] == 0

    qep = parser("select * from stories where id = 1 or id = 2")
    assert qep.plan["Node Type"] == "Bitmap Heap Scan"
    assert qep.plan["Relation Name"] == "stories"
    assert qep.plan["Alias"] == "stories"
    assert qep.plan["Actual Rows"] == 2

    qep = parser("select * from users where id = 1 or id = 2")
    assert qep.plan["Node Type"] == "Bitmap Heap Scan"
    assert qep.plan["Relation Name"] == "users"
    assert qep.plan["Alias"] == "users"
    assert qep.plan["Actual Rows"] == 2
