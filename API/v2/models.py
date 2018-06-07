"""Creates the database models with ability to perform SQL functions"""

import v1.models
from datetime import datetime
from run import connection, cursor


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
        cursor.execute("DELETE FROM %s", (cls.__table__,))

        connection.commit()

    def deserialize(self, **dictionary):
        """ Create a model object from the dictionary,
            Override this method to do the conversion custom
        """
        return self.__dict__.update(dictionary)

    @classmethod
    def query_all(cls):
        """
        Query all items from the database
        :return:
        """
        cursor.execute("SELECT * FROM {}".format(cls.__table__))
        items = cursor.fetchall()
        return [cls.deserialize(x) for x in items]

    @classmethod
    def query_by_field(cls, field, value):
        """
        Query items from the database based on a particular field
        :param field:
        :param value:
        :return:
        """
        cursor.execute("SELECT * FROM %s WHERE %s = %s", (cls.__table__, field, value))
        items = cursor.fetchall()

        return [cls.deserialize(x) for x in items]

    @classmethod
    def query_by_id(cls, _id):
        """
        Query items from the database by id
        :param _id:
        :return:
        """
        cursor.execute("SELECT * FROM %s WHERE id = %s", (cls.__table__, _id))
        item = cursor.fetchone()
        if item is None:
            return None
        return cls.deserialize(item)

    def save(self):
        """ Save an item to the database"""
        pass

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
        cursor.execute("DELETE FROM %s WHERE id = %s", (self.__table__, self.id))
        connection.commit()


class User(v1.models.User, DBBaseModel):
    """
    Creates a user with different roles
    """
    __table__ = "users"

    @classmethod
    def migrate(cls):
        cursor.execute("""CREATE TABLE IF NOT EXISTS users(
            id serial PRIMARY KEY ,
            firstname varchar,
            lastname varchar,
            username varchar,
            email varchar,
            password varchar,
            created_at timestamp,
            updated_at timestamp,
            role varchar)""")
        connection.commit()

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
        cursor.execute(
            "INSERT INTO users(firstname,lastname,username,email,"
            "password,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s)", (
                self.firstname, self.lastname, self.username, self.email,
                self.password, self.created_at,
                self.updated_at
            ))
        connection.commit()

    def update(self):
        """
        Update the details of the user
        :return:
        """
        super().update()
        cursor.execute(
            "UPDATE users SET firstname = %s, lastname = %s, username = %s,"
            "email = %s, password = %s, updated_at = now() where id = %s", (
                self.firstname, self.lastname, self.username,
                self.email, self.password,
                self.id))
        connection.commit()

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


class Request(v1.models.Request, DBBaseModel):
    """
    Contains the maintenance/repair request
    """
    __table__ = "requests"

    @classmethod
    def migrate(cls):
        cursor.execute("""CREATE TABLE IF NOT EXISTS requests(
          id serial PRIMARY KEY ,
          product_name varchar,
          description varchar,
          status varchar,
          photo varchar,
          created_by INTEGER,
          created_at TIMESTAMP,
          updated_at TIMESTAMP,
          FOREIGN KEY (created_by) REFERENCES users(id))""")
        connection.commit()

    def save(self):
        """
        Save the request into the database
        :return:
        """
        cursor.execute(
            "INSERT INTO requests(product_name,description,status,photo,created_by,created_at,updated_at)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s)", (
                self.product_name,
                self.description,
                self.status,
                self.photo,
                self.created_by,
                self.created_at,
                self.updated_at
            ))
        connection.commit()

    def update(self):
        super().update()
        cursor.execute(
            "UPDATE requests SET product_name = %s, description = %s, "
            "status = %s, photo = %s, updated_at = now() WHERE id = %s", (
                self.product_name,
                self.description,
                self.status,
                self.photo,
                self.id
            )
        )
        connection.commit()

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
        cursor.execute("""CREATE TABLE IF NOT EXISTS feedback(
          id serial PRIMARY KEY ,
          admin INTEGER,
          request INTEGER,
          message varchar,
          created_at timestamp,
          updated_at TIMESTAMP,
          foreign key (admin) references users(id),
          foreign key (request) references requests(id)
        )""")
        connection.commit()

    def save(self):
        """
        Saves a feedback to the feedback table
        :return:
        """
        cursor.execute("INSERT INTO feedback(admin, request, message, created_at, updated_at) "
                       "VALUES(%s,%s,%s,%s,%s)", (
                           self.admin,
                           self.request,
                           self.message,
                           self.created_at,
                           self.updated_at
                       ))
        connection.commit()

    def update(self):
        super().update()
        cursor.execute(
            "UPDATE feedback SET admin = %s, request = %s, message = %s, updated_at = now() WHERE id = %d",
            (
                self.admin,
                self.request,
                self.message,
                self.id
            ))

    def maintenance_request(self):
        """
        Returns the request for this Feedback
        :return:
        """
        return Request.query_by_id(self.request)


class Notification(v1.models.Notification, DBBaseModel):
    """
    Stores the unread and the read notifications for the user
    """
    __table__ = "notifications"

    @classmethod
    def migrate(cls):
        """
        Create the Notifications Table
        :return:
        """
        cursor.execute("""CREATE TABLE IF NOT EXISTS notifications(
            id serial PRIMARY KEY ,
            admin_id INTEGER,
            user_id INTEGER,
            message varchar,
            read boolean,
            created_at timestamp,
            updated_at timestamp,
            FOREIGN KEY (admin_id) references users(id),
            FOREIGN KEY (user_id) references users(id)
        )""")
        connection.commit()

    def save(self):
        """
        Save the notification into the database
        :return:
        """
        cursor.execute(
            "INSERT INTO notifications(admin_id,user_id,message,read, created_at, updated_at) VALUES(%s,%s,%s,%s,%s,%s)",
            (
                self.admin,
                self.user,
                self.message,
                False,
                self.created_at,
                self.updated_at
            ))
        connection.commit()

    def update(self):
        """
        Update the notification in the database
        :return:
        """
        super().update()
        cursor.execute("UPDATE notifications SET message = %s, read = %s, updated_at = now()", (
            self.message,
            self.read
        ))
        connection.commit()

    def mark_as_read(self):
        """
        Mark a notification as read
        :return:
        """
        self.read = True
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
    def migrate(cls):
        """
        Create the table to store the blacklisted tokens
        :return:
        """
        cursor.execute("""CREATE TABLE IF NOT EXISTS blacklist(
          id serial PRIMARY KEY ,
          token varchar)""")
        connection.commit()

    def save(self):
        """
        Saves a token into the database
        :return:
        """

        cursor.execute("INSERT INTO blacklist(token) VALUES(%S)", (self.token,))
        connection.commit()
