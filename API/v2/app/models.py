"""Creates the database models with ability to perform SQL functions"""
import uuid

import psycopg2

from passlib.handlers.bcrypt import bcrypt

import v1.models
from datetime import datetime
from run import db


class DBBaseModel(v1.models.BaseModel):
    """
    Base Database models for transactions
    """
    __table__ = ""

    def __init__(self, created_at, updated_at):
        super().__init__(created_at, updated_at)

    @classmethod
    def migrate(cls):
        """
        Create the tables here
        :return:
        """
        pass

    @classmethod
    def rollback(cls):
        """
        Deletes all the data from the tables
        :param cls:
        :return:
        """
        db.cursor.execute("DELETE FROM {}".format(cls.__table__))

        db.connection.commit()

    @classmethod
    def deserialize(cls, dictionary):
        """ Create a model object from the dictionary,
            Override this method to do the conversion custom
        """
        return cls(datetime.now(), datetime.now())

    @classmethod
    def query_all(cls, page=1, number_of_items=100):
        """
        Query all items from the database for a particular page
        :param number_of_items:
        :param page:
        :return:
        """
        offset = number_of_items * (int(page) - 1)
        db.cursor.execute(
            "SELECT * FROM {}  ORDER BY updated_at DESC LIMIT {} OFFSET {}".format(cls.__table__, number_of_items,
                                                                                   offset))
        try:
            items = db.cursor.fetchall()
            return [cls.deserialize(x) for x in items]
        except psycopg2.ProgrammingError:
            return []

    @classmethod
    def query_one_by_field(cls, field, value):
        """Get one item from the database"""
        items = cls.query_by_field(field, value)
        if len(items) == 0:
            return None
        return items[0]

    @classmethod
    def count_all(cls):
        """
        Counts the total number of items in the database
        :return:
        """
        db.cursor.execute("SELECT COUNT(*) as count FROM {}".format(cls.__table__))
        result = db.cursor.fetchone()
        return result['count']

    @classmethod
    def count_all_by_field(cls, field, value):
        """
        Query all after filtering
        :param field:
        :param value:
        :return:
        """
        db.cursor.execute("SELECT COUNT(*) as count FROM {0} WHERE {1} = %s"
                          .format(cls.__table__, field), (value,))
        result = db.cursor.fetchone()
        return result['count']

    @classmethod
    def query_by_field(cls, field, value, page=1, number_of_items=100):
        """
        Query items from the database based on a particular field
        :param page:
        :param number_of_items:
        :param field:
        :param value:
        :return:
        """
        offset = number_of_items * (int(page) - 1)
        db.cursor.execute(
            "SELECT * FROM {0} WHERE {1} = %s  ORDER BY updated_at DESC LIMIT {2} OFFSET {3}".format(cls.__table__,
                                                                                                     field,
                                                                                                     number_of_items,
                                                                                                     offset), (value,))
        try:
            items = db.cursor.fetchall()

            return [cls.deserialize(x) for x in items]
        except psycopg2.ProgrammingError:
            return []

    @classmethod
    def query_by_id(cls, _id):
        """
        Query items from the database by id
        :param _id:
        :return:
        """
        db.cursor.execute("SELECT * FROM {} WHERE id = %s".format(cls.__table__), (_id,))
        try:
            item = db.cursor.fetchone()
            if item is None:
                return None
            return cls.deserialize(item)
        except psycopg2.ProgrammingError:
            return None

    def save(self):
        """ Save an item to the database"""
        result = db.cursor.fetchone()
        if result is not None:
            self.id = result['id']
        db.connection.commit()

    def update(self):
        """
        Updates the details of an item
        :return:
        """
        self.updated_at = datetime.now()
        pass

    def delete(self):
        """
        Deletes an item from the database
        :return:
        """
        db.cursor.execute("DELETE FROM {} WHERE id = %s".format(self.__table__), (self.id))
        db.connection.commit()


class User(v1.models.User, DBBaseModel):
    """
    Creates a user with different roles
    """
    __table__ = "users"

    def __init__(self, firstname="", lastname="", email="", username="", password="", profile_picture="",
                 created_at=datetime.now(), updated_at=datetime.now()):
        super().__init__(firstname=firstname, lastname=lastname, email=email, password=password, username=username,
                         created_at=created_at, updated_at=updated_at, profile_picture=profile_picture)

        self.verify_token = uuid.uuid4().hex[:6].upper()
        self.verified = 0

    @classmethod
    def migrate(cls):
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS users(
            id serial PRIMARY KEY ,
            firstname varchar,
            lastname varchar,
            username varchar,
            email varchar,
            password varchar,
            created_at timestamp,
            updated_at timestamp,
            verify_token varchar,
            verified integer,
            role varchar)""")
        db.connection.commit()

    @classmethod
    def deserialize(cls, dictionary):
        user = User()
        user.id = dictionary['id']
        user.firstname = dictionary['firstname']
        user.lastname = dictionary['lastname']
        user.username = dictionary['username']
        user.email = dictionary['email']
        user.password = dictionary['password']
        user.created_at = dictionary['created_at']
        user.updated_at = dictionary['updated_at']
        user.role = dictionary['role']
        user.verify_token = dictionary['verify_token']
        user.verified = dictionary['verified']

        return user

    @staticmethod
    def get_by_username(username):
        """
        Get user based on the username
        :param username:
        :return:
        """
        return User.query_by_field("username", username)

    def save(self):
        """
        Save the user into the database
        :return:
        """
        db.cursor.execute(
            "INSERT INTO users(firstname,lastname,username,email,"
            "password,created_at,updated_at,verify_token, verified, role) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s, %s) RETURNING id", (
                self.firstname, self.lastname, self.username, self.email,
                self.password, self.created_at,
                self.updated_at, self.verify_token, self.verified, self.role
            ))
        super().save()

    def update(self):
        """
        Update the details of the user
        :return:
        """
        super().update()
        db.cursor.execute(
            "UPDATE users SET firstname = %s, lastname = %s, username = %s,"
            "email = %s, password = %s, updated_at = now(), role = %s, verify_token = %s, verified = %s where id = %s",
            (
                self.firstname, self.lastname, self.username,
                self.email, self.password, self.role,
                self.verify_token, self.verified,
                self.id))
        db.connection.commit()

    def requests(self):
        """
        Get all the requests for this user
        :return:
        """
        return Request.query_by_field("created_by", self.id)

    def is_admin(self):
        """
        To check whether a user is an administrator
        :return:
        """
        return self.role == User.ROLE_ADMINISTRATOR

    def notifications(self):
        """
        Get all the notifications sent to this user
        :return:
        """

        items = []
        if self.id != 1:
            items = Notification.query_by_field("user_id", self.id)
        if User.query_by_id(self.id).is_admin():
            items = items + Notification.query_by_field("user_id", 1)
        return items

    def read_notifications(self):
        """
        Get all the read notifications
        :return:
        """
        return [x for x in self.notifications() if x.read == 1]

    def unread_notifications(self):
        """
        Get all the unread notifications for this user
        :return:
        """
        return [x for x in self.notifications() if not x.read == 1]

    def verify_user(self, verify_token):
        if self.verify_token == verify_token:
            self.verified = 1
            return True
        return False

    def excluded_fields(self):
        return ['password', 'created_at', 'updated_at', "verify_token"]


class Admin(User):
    """
    Contains implementation for creating a default admin from the super class
    """

    def __init__(self, firstname="", lastname="", email="", username="", password="", profile_picture="",
                 created_at=datetime.now(), updated_at=datetime.now()):
        super().__init__(firstname, lastname, email, username, password, profile_picture, created_at, updated_at)
        self.role = User.ROLE_ADMINISTRATOR

    @staticmethod
    def default():
        admin = Admin()
        admin.firstname = db.app.config['DEFAULT_ADMIN_FIRST_NAME']
        admin.lastname = db.app.config['DEFAULT_ADMIN_LAST_NAME']
        admin.email = db.app.config['DEFAULT_ADMIN_EMAIL']
        admin.username = db.app.config['DEFAULT_ADMIN_USER_NAME']
        admin.password = bcrypt.encrypt(db.app.config['DEFAULT_ADMIN_PASSWORD'])
        admin.profile_picture = db.app.config['DEFAULT_ADMIN_PROFILE_PICTURE']
        admin.verified = 1

        return admin


class Request(v1.models.Request, DBBaseModel):
    """
    Contains the maintenance/repair request
    """
    __table__ = "requests"

    @classmethod
    def migrate(cls):
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS requests(
          id serial PRIMARY KEY ,
          product_name varchar,
          description varchar,
          status varchar,
          photo varchar,
          created_by INTEGER,
          created_at TIMESTAMP,
          updated_at TIMESTAMP,
          FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE)""")
        db.connection.commit()

    @classmethod
    def deserialize(cls, dictionary):
        request = Request()
        request.id = dictionary['id']
        request.product_name = dictionary['product_name']
        request.description = dictionary['description']
        request.status = dictionary['status']
        request.photo = dictionary['photo']
        request.created_by = dictionary['created_by']
        request.created_at = dictionary['created_at']
        request.updated_at = dictionary['updated_at']

        return request

    def save(self):
        """
        Save the request into the database
        :return:
        """
        db.cursor.execute(
            "INSERT INTO requests(product_name,description,status,photo,created_by,created_at,updated_at)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id", (
                self.product_name,
                self.description,
                self.status,
                self.photo,
                self.created_by,
                self.created_at,
                self.updated_at
            ))
        super().save()

    def update(self):
        super().update()
        db.cursor.execute(
            "UPDATE requests SET product_name = %s, description = %s, "
            "status = %s, photo = %s, updated_at = now() WHERE id = %s", (
                self.product_name,
                self.description,
                self.status,
                self.photo,
                self.id
            )
        )
        db.connection.commit()

    def approve(self):
        """
        Mark a request as approved
        :return:
        """
        self.status = Request.STATUS_APPROVED
        self.update()

    def disapprove(self):
        """
        Mark a request as disapproved
        :return:
        """
        self.status = Request.STATUS_DISAPPROVED
        self.update()

    def resolve(self):
        """
        Mark a request as resolved
        :return:
        """
        self.status = Request.STATUS_RESOLVED
        self.update()

    def feedback(self):
        """
        Gets the feedback associated with this request
        :return:
        """
        return Feedback.query_by_field("request", self.id)

    @classmethod
    def query_for_user(cls, user_id):
        """
        Gets all the requests for this user
        :param user_id:
        :return:
        """
        return Request.query_by_field("created_by", user_id)

    @classmethod
    def query_and_filter(cls, from_date, to_date, query='', status='all', page=1, number_of_items=100, user_id=-1):
        """
        Query the requests and filter them
        :param from_date:
        :param to_date:
        :param query:
        :param status:
        :param page:
        :param number_of_items:
        :return:
        """

        data = {"from_date": from_date, "to_date": to_date, "query": "%{}%".format(query), "status": status,
                "user_id": user_id}
        offset = number_of_items * (int(page) - 1)
        sql = "SELECT * FROM {} ".format(cls.__table__)
        count_sql = "SELECT COUNT(*) as count from {} ".format(cls.__table__)

        queries = []
        if status != "all":
            queries.append(" LOWER(status) = LOWER(%(status)s)")
        if from_date:
            queries.append(" CAST(created_at AS DATE) >= %(from_date)s")
        if to_date:
            queries.append(" CAST(created_at AS DATE) <= %(to_date)s")
        if query:
            queries.append(" product_name LIKE %(query)s")
        if user_id != -1:
            queries.append(" created_by = %(user_id)s")

        for i in range(len(queries)):
            if i == 0:
                sql = sql + " WHERE " + queries[i]
                count_sql = count_sql + " WHERE " + queries[i]
            else:
                sql = sql + " AND " + queries[i]
                count_sql = count_sql + " AND " + queries[i]

        sql = sql + " ORDER BY updated_at DESC LIMIT {} OFFSET {}".format(number_of_items, offset)

        db.cursor.execute(sql, data)

        items = db.cursor.fetchall()

        db.cursor.execute(count_sql, data)
        count = db.cursor.fetchone()

        return [cls.deserialize(x) for x in items], count['count']


class Feedback(v1.models.Feedback, DBBaseModel):
    """
    Stores the feedback to the requests
    """
    __table__ = "feedback"

    @classmethod
    def migrate(cls):
        """
        Creates the feedback table
        :return:
        """
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS feedback(
          id serial PRIMARY KEY ,
          admin INTEGER,
          request INTEGER,
          message varchar,
          created_at timestamp,
          updated_at TIMESTAMP,
          foreign key (admin) references users(id) ON DELETE CASCADE,
          foreign key (request) references requests(id) ON DELETE CASCADE
        )""")
        db.connection.commit()

    @classmethod
    def deserialize(cls, dictionary):
        feedback = Feedback()
        feedback.id = dictionary['id']
        feedback.admin = dictionary['admin']
        feedback.request = dictionary['request']
        feedback.message = dictionary['message']
        feedback.created_at = dictionary['created_at']
        feedback.updated_at = dictionary['updated_at']

        return feedback

    def save(self):
        """
        Saves a feedback to the feedback table
        :return:
        """
        db.cursor.execute("INSERT INTO feedback(admin, request, message, created_at, updated_at) "
                          "VALUES(%s,%s,%s,%s,%s) RETURNING id", (
                              self.admin,
                              self.request,
                              self.message,
                              self.created_at,
                              self.updated_at
                          ))

        super().save()

    def update(self):
        super().update()
        db.cursor.execute(
            "UPDATE feedback SET admin = %s, request = %s, message = %s, updated_at = now() WHERE id = %d",
            (
                self.admin,
                self.request,
                self.message,
                self.id
            ))

    def created_by(self):
        """
        Returns the admin who posted the feedback
        :return:
        """
        return User.query_by_id(self.admin)

    def maintenance_request(self):
        """
        Returns the request for this Feedback
        :return:
        """
        return Request.query_by_id(self.request)

    @classmethod
    def all_for_user(cls, user_id, page, number_of_items):
        """
        Query items from the database based on a particular field
        :param user_id:
        :return:
        """
        offset = number_of_items * (int(page) - 1)

        count_sql = "SELECT COUNT(feedback.*) as count from feedback inner join requests on " \
                    "requests.created_by = %s and requests.id = feedback.request;"

        sql = "SELECT feedback.*  from feedback inner join requests on " \
              "requests.created_by = %s and requests.id = feedback.request ORDER BY updated_at LIMIT {} OFFSET {};" \
            .format(number_of_items, offset)

        db.cursor.execute(sql, (user_id,))

        items = db.cursor.fetchall()

        db.cursor.execute(count_sql, (user_id,))
        count = db.cursor.fetchone()
        return [cls.deserialize(x) for x in items], count['count']


class Notification(v1.models.Notification, DBBaseModel):
    """
    Stores the unread and the read notifications for the user
    """
    __table__ = "notifications"

    def __init__(self, admin=None, user=None, message="", action="", created_at=datetime.now(),
                 updated_at=datetime.now()):
        super().__init__(admin=admin, user=user, message=message, created_at=created_at, updated_at=updated_at);
        self.action = action

    @classmethod
    def migrate(cls):
        """
        Create the Notifications Table
        :return:
        """
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS notifications(
            id serial PRIMARY KEY ,
            admin_id INTEGER,
            user_id INTEGER,
            message varchar,
            action varchar,
            read integer,
            created_at timestamp,
            updated_at timestamp,
            FOREIGN KEY (admin_id) references users(id),
            FOREIGN KEY (user_id) references users(id) ON DELETE CASCADE
        )""")
        db.connection.commit()

    @classmethod
    def deserialize(cls, dictionary):
        notification = Notification()
        notification.id = dictionary['id']
        notification.admin = dictionary['admin_id']
        notification.user = dictionary['user_id']
        notification.message = dictionary['message']
        notification.read = dictionary['read']
        notification.action = dictionary['action'];
        notification.updated_at = dictionary['updated_at']
        notification.created_at = dictionary['created_at']

        return notification

    def save(self):
        """
        Save the notification into the database
        :return:
        """
        db.cursor.execute(
            "INSERT INTO notifications(admin_id,user_id,message,read,action, created_at, updated_at) "
            "VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id;",
            (
                self.admin,
                self.user,
                self.message,
                0,
                self.action,
                self.created_at,
                self.updated_at
            ))
        super().save()

    def update(self):
        """
        Update the notification in the database
        :return:
        """
        super().update()
        db.cursor.execute(
            "UPDATE notifications SET message = %s, read = %s, action = %s, updated_at = now() WHERE id = %s", (
                self.message,
                self.read,
                self.action,
                self.id
            ))
        db.connection.commit()

    def mark_as_read(self):
        """
        Mark a notification as read
        :return:
        """
        self.read = 1
        self.update()

    def get_admin(self):
        """
        Get the Admin that created this notification
        :return:
        """
        return User.query_by_id(self.admin)

    def get_user(self):
        """
        Get the User that received this notification
        :return:
        """
        return User.query_by_id(self.user)

    @classmethod
    def query_all_for_user(cls, user_id):
        """
        Returns all the notifications sent to this a user
        :param user_id:
        :return:
        """
        return Notification.query_by_field("user_id", user_id)


class Blacklist(DBBaseModel):
    """
    Contains the list of blacklisted tokens when a user logs out
    """
    __table__ = "blacklist"

    def __init__(self, token):
        super().__init__(datetime.now(), datetime.now())
        self.token = token

    @classmethod
    def deserialize(cls, dictionary):
        blacklist = Blacklist()
        blacklist.id = dictionary['id']
        blacklist.token = dictionary['token']

        return blacklist

    @classmethod
    def migrate(cls):
        """
        Create the table to store the blacklisted tokens
        :return:
        """
        db.cursor.execute("""CREATE TABLE IF NOT EXISTS blacklist(
          id serial PRIMARY KEY ,
          token varchar)""")
        db.connection.commit()

    def save(self):
        """
        Saves a token into the database
        :return:
        """

        db.cursor.execute("INSERT INTO blacklist(token) VALUES(%s)", (self.token,))
        db.connection.commit()
