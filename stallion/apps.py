import pyspark.sql.functions as f
import pyspark.sql.types as t
from pyspark.sql import Window
from stallion.py_filter_fxs import *


def Flag_DUP_Applicant(SRT, sdf_inp, DAY=28):
    """
    This is the Python translation of the SAS Code `Flag_DUP_Applicant.sas`.
    """
    if SRT.upper() == "ASCENDING":
        sdf_0 = sdf_inp\
            .repartition(1)\
            .orderBy([f.col("IDKey").asc(),
                      f.col("APP_Date").asc(),
                      f.col("DUP_Application").asc()])

        windowspecIDKEY = Window \
            .partitionBy(f.col("IDKey")) \
            .orderBy([f.col("IDKey").asc(),
                      f.col("APP_Date").asc(),
                      f.col("DUP_Application").asc()])

        # windowspecAPPDATE = Window \
        #     .partitionBy(f.col("IDKey")) \
        #     .orderBy(f.col("IDKey").asc(),
        #              f.col("APP_Date").asc(),
        #              f.col("DUP_Application").asc())

        sdf_1 = sdf_0 \
            .repartition(1) \
            .withColumn("RET_IDKey", f.lag(f.col("IDKey"), 1).over(windowspecIDKEY))\
            .withColumn("RET_Date", f.lag(f.col("APP_Date"), 1).over(windowspecIDKEY))\
            .withColumn("DUP_Applicant", f.when(f.col("IDKey") == f.col("RET_IDKey"), f.lit("Y"))
                                          .otherwise(f.lit(None)))
    else:
        sdf_0 = sdf_inp\
            .repartition(1)\
            .orderBy([f.col("IDKey").asc(),
                      f.col("APP_Date").desc(),
                      f.col("DUP_Application").desc()])

        windowspecIDKEY = Window \
            .partitionBy(f.col("IDKey")) \
            .orderBy([f.col("IDKey").asc(),
                      f.col("APP_Date").desc(),
                      f.col("DUP_Application").desc()])

        # windowspecAPPDATE = Window \
        #     .partitionBy(f.col("IDKey")) \
        #     .orderBy(f.col("IDKey").asc(),
        #              f.col("APP_Date").desc(),
        #              f.col("DUP_Application").desc())

        sdf_1 = sdf_0 \
            .repartition(1) \
            .withColumn("RET_IDKey", f.lag(f.col("IDKey"), 1).over(windowspecIDKEY)) \
            .withColumn("RET_Date", f.lag(f.col("APP_Date"), 1).over(windowspecIDKEY))\
            .withColumn("DUP_Applicant", f.when(f.col("IDKey") == f.col("RET_IDKey"), f.lit("Y"))
                                          .otherwise(f.lit(None)))

    if SRT.upper() == "ASCENDING":
        sdf_2 = sdf_1\
            .withColumn("DUP_DaysBetweenApplications", f.when(f.col("IDKey") == f.col("RET_IDKey"),
                                                              f.datediff(f.col("APP_Date"), f.col("RET_Date")))
                                                        .otherwise(f.lit(None)))
    else:
        sdf_2 = sdf_1 \
            .withColumn("DUP_DaysBetweenApplications", f.when(f.col("IDKey") == f.col("RET_IDKey"),
                                                              f.datediff(f.col("RET_Date"), f.col("APP_Date")))
                                                        .otherwise(f.lit(None)))

    sdf_3 = sdf_2\
        .withColumn("DUP_Application", f.when((f.col("DUP_DaysBetweenApplications") >= f.lit(0)) &
                                              (f.col("DUP_DaysBetweenApplications") <= f.lit(DAY)), f.lit(1))
                                        .otherwise(f.col("DUP_Application")))\
        .drop(*["RET_IDKey", "APP_Date"])

    return sdf_3


def DUP_subroutine(sdf_inp):
    """
    This is the Python translation of STEP 4 in `Input_Applications_DMP.sas`.
    In STEP 4, we sort by the optimal decision services outcome, best risk grade obtained, and highest subscription
    limit within the acceptable period.
    """
    def change_day():
        return lambda x: x.replace(day=1)
    udf_change_day = f.udf(change_day, returnType=t.DateType())

    sdf_0 = sdf_inp\
        .repartition(1)\
        .orderBy([f.col("IDKey").asc(),
                  f.col("DUP_Application").asc(),
                  f.col("Filter_Decision_Outcome_SEQ").asc(),
                  f.col("APP_RiskGrade").asc(),
                  f.col("APP_SubscriptionLimit").desc(),
                  f.col("APP_Date").asc()])

    windowspecIDKEY = Window \
        .partitionBy(f.col("IDKey")) \
        .orderBy([f.col("IDKey").asc(),
                  f.col("DUP_Application").asc(),
                  f.col("Filter_Decision_Outcome_SEQ").asc(),
                  f.col("APP_RiskGrade").asc(),
                  f.col("APP_SubscriptionLimit").desc(),
                  f.col("APP_Date").asc()])

    sdf_1 = sdf_0\
        .withColumn("RET_IDKey", f.lag(f.col("IDKey"), 1).over(windowspecIDKEY))\
        .withColumn("RET_Date", f.lag(f.col("APP_Date"), 1).over(windowspecIDKEY))\
        .withColumn("RET_Application", f.lag(f.col("DUP_Application"), 1).over(windowspecIDKEY))\
        .withColumn("APP_Month_dte", f.to_date(f.col("APP_Month"), "yyyyMMdd"))\
        .withColumn("APP_Month_dte", udf_change_day(f.col("APP_Month_dte")))\
        .withColumn("RET_Month", f.lag(f.col("APP_Month"), 1).over(windowspecIDKEY))\
        .withColumn("RET_Month_dte", f.to_date(f.col("RET_Month"), "yyyyMMdd"))\
        .withColumn("RET_Month_dte", udf_change_day(f.col("RET_Month_dte")))\
        .withColumn("RET_DecisionOutcome", f.lag(f.col("Filter_Decision_Outcome_SEQ"), 1).over(windowspecIDKEY))\
        .withColumn("RET_RiskGrade", f.lag(f.col("APP_RiskGrade"), 1).over(windowspecIDKEY))

    sdf_2 = sdf_1\
        .withColumn("DUP_DaysBetweenApplications", f.when((f.col("IDKey") == f.col("RET_IDKey")) &
                                                          (f.col("RET_Application") == 1),
                                                          f.datediff(f.col("APP_Date"), f.col("RET_Date")))
                                                    .otherwise(f.lit(None)))\
        .withColumn("DUP_Applicant", f.when((f.col("IDKey") == f.col("RET_IDKey")) &
                                            (f.col("RET_Application") == 1),
                                            f.lit("Z"))
                                      .otherwise(f.col("DUP_Applicant")))\
        .withColumn("DUP_CalendarMonthsSkipped", f.when((f.col("IDKey") == f.col("RET_IDKey")) &
                                                        (f.col("RET_Application") == 1) &
                                                        (f.col("APP_Month") != f.col("RET_Month")),
                                                        f.months_between(f.col("APP_Month_dte"), f.col("RET_Month_dte")))
                                                  .otherwise(f.lit(None)))\
        .withColumn("DUP_DecisionOutcome", f.when((f.col("IDKey") == f.col("RET_IDKey")) &
                                                  (f.col("RET_Application") == 1) &
                                                  f.col("Filter_Decision_Outcome_SEQ").isin([1, 2, 3]) &
                                                  f.col("RET_DecisionOutcome").isin([1, 2, 3]) &
                                                  (f.col("Filter_Decision_Outcome_SEQ") != f.col("RET_DecisionOutcome")),
                                                  f.col("RET_DecisionOutcome") - f.col("Filter_Decision_Outcome_SEQ"))
                                            .otherwise(f.lit(None)))\
        .withColumn("DUP_RiskGrade", f.when((f.col("IDKey") == f.col("RET_IDKey")) &
                                            (f.col("RET_Application") == 1) &
                                            f.col("APP_RiskGrade").isNotNull() &
                                            f.col("RET_RiskGrade").isNotNull() &
                                            (f.col("APP_RiskGrade") != f.col("RET_RiskGrade")),
                                            f.col("RET_RiskGrade").astype(int) - f.col("APP_RiskGrade").astype(int))
                                      .otherwise(f.lit(None)))\
        .drop(*["RET_IDKey",
                "RET_Date",
                "RET_Application",
                "RET_Month",
                "RET_DecisionOutcome",
                "RET_RiskGrade"])

    return sdf_2


def Applications_Contracts_Update(NBR, Account, APP_Account_Number1, APP_Account_Number2, APP_Account_Number3,
                                  Subscriber_Number, CON_Start_Date, Matched_Distance, CON_Period):
    APP_Subscriptions = NBR

    APP_Subscriber_Number1 = APP_Subscriber_Number2 = APP_Subscriber_Number3 = APP_Subscriber_Number4 = APP_Subscriber_Number5 = None
    APP_Activation_Date1 = APP_Activation_Date2 = APP_Activation_Date3 = APP_Activation_Date4 = APP_Activation_Date5 = None
    APP_Activation_Weeks1 = APP_Activation_Weeks2 = APP_Activation_Weeks3 = APP_Activation_Weeks4 = APP_Activation_Weeks5 = None
    APP_Activation_Month1 = APP_Activation_Month2 = APP_Activation_Month3 = APP_Activation_Month4 = APP_Activation_Month5 = None

    if NBR == 1:
        if APP_Account_Number1 == Account:
            APP_Account1 = "1"
        elif APP_Account_Number2 == Account:
            APP_Account1 = "2"
        elif APP_Account_Number3 == Account:
            APP_Account1 = "3"
        elif APP_Account_Number1 is None:
            APP_Account_Number1 = Account
            APP_Account1 = "1"
        elif APP_Account_Number2 is None:
            APP_Account_Number2 = Account
            APP_Account1 = "1"
        elif APP_Account_Number3 is None:
            APP_Account_Number3 = Account
            APP_Account1 = "1"
        else:
            APP_Account1 = None
        APP_Accounts = APP_Account1
        APP_Subscriber_Number1 = Subscriber_Number
        APP_Activation_Date1 = CON_Start_Date
        APP_Activation_Days1 = Matched_Distance
        if APP_Activation_Days1 == 0:
            APP_Activation_Weeks1 = 0
        if APP_Activation_Days1 <= -1:
            APP_Activation_Weeks1 = int((APP_Activation_Days1 + 1) / 7) - 1
        if APP_Activation_Days1 >= 1:
            APP_Activation_Weeks1 = int((APP_Activation_Days1 - 1) / 7) + 1
        APP_Activation_Month1 = CON_Period
    elif NBR == 2:
        if APP_Account_Number1 == Account:
            APP_Account2 = "1"
        elif APP_Account_Number2 == Account:
            APP_Account2 = "2"
        elif APP_Account_Number3 == Account:
            APP_Account2 = "3"
        elif APP_Account_Number1 is None:
            APP_Account_Number1 = Account
            APP_Account2 = "1"
        elif APP_Account_Number2 is None:
            APP_Account_Number2 = Account
            APP_Account2 = "1"
        elif APP_Account_Number3 is None:
            APP_Account_Number3 = Account
            APP_Account2 = "1"
        else:
            APP_Account2 = None
        APP_Accounts = APP_Account2
        APP_Subscriber_Number2 = Subscriber_Number
        APP_Activation_Date2 = CON_Start_Date
        APP_Activation_Days2 = Matched_Distance
        if APP_Activation_Days2 == 0:
            APP_Activation_Weeks2 = 0
        if APP_Activation_Days2 <= -1:
            APP_Activation_Weeks2 = int((APP_Activation_Days2 + 1) / 7) - 1
        if APP_Activation_Days2 >= 1:
            APP_Activation_Weeks2 = int((APP_Activation_Days2 - 1) / 7) + 1
        APP_Activation_Month2 = CON_Period
    elif NBR == 3:
        if APP_Account_Number1 == Account:
            APP_Account3 = "1"
        elif APP_Account_Number2 == Account:
            APP_Account3 = "2"
        elif APP_Account_Number3 == Account:
            APP_Account3 = "3"
        elif APP_Account_Number1 is None:
            APP_Account_Number1 = Account
            APP_Account3 = "1"
        elif APP_Account_Number2 is None:
            APP_Account_Number2 = Account
            APP_Account3 = "1"
        elif APP_Account_Number3 is None:
            APP_Account_Number3 = Account
            APP_Account3 = "1"
        else:
            APP_Account3 = None
        APP_Accounts = APP_Account3
        APP_Subscriber_Number3 = Subscriber_Number
        APP_Activation_Date3 = CON_Start_Date
        APP_Activation_Days3 = Matched_Distance
        if APP_Activation_Days3 == 0:
            APP_Activation_Weeks3 = 0
        if APP_Activation_Days3 <= -1:
            APP_Activation_Weeks3 = int((APP_Activation_Days3 + 1) / 7) - 1
        if APP_Activation_Days3 >= 1:
            APP_Activation_Weeks3 = int((APP_Activation_Days3 - 1) / 7) + 1
        APP_Activation_Month3 = CON_Period
    elif NBR == 4:
        if APP_Account_Number1 == Account:
            APP_Account4 = "1"
        elif APP_Account_Number2 == Account:
            APP_Account4 = "2"
        elif APP_Account_Number3 == Account:
            APP_Account4 = "3"
        elif APP_Account_Number1 is None:
            APP_Account_Number1 = Account
            APP_Account4 = "1"
        elif APP_Account_Number2 is None:
            APP_Account_Number2 = Account
            APP_Account4 = "1"
        elif APP_Account_Number3 is None:
            APP_Account_Number3 = Account
            APP_Account4 = "1"
        else:
            APP_Account4 = None
        APP_Accounts = APP_Account4
        APP_Subscriber_Number4 = Subscriber_Number
        APP_Activation_Date4 = CON_Start_Date
        APP_Activation_Days4 = Matched_Distance
        if APP_Activation_Days4 == 0:
            APP_Activation_Weeks4 = 0
        if APP_Activation_Days4 <= -1:
            APP_Activation_Weeks4 = int((APP_Activation_Days4 + 1) / 7) - 1
        if APP_Activation_Days4 >= 1:
            APP_Activation_Weeks4 = int((APP_Activation_Days4 - 1) / 7) + 1
        APP_Activation_Month4 = CON_Period
    else:
        if APP_Account_Number1 == Account:
            APP_Account5 = "1"
        elif APP_Account_Number2 == Account:
            APP_Account5 = "2"
        elif APP_Account_Number3 == Account:
            APP_Account5 = "3"
        elif APP_Account_Number1 is None:
            APP_Account_Number1 = Account
            APP_Account5 = "1"
        elif APP_Account_Number2 is None:
            APP_Account_Number2 = Account
            APP_Account5 = "1"
        elif APP_Account_Number3 is None:
            APP_Account_Number3 = Account
            APP_Account5 = "1"
        else:
            APP_Account5 = None
        APP_Accounts = APP_Account5
        APP_Subscriber_Number5 = Subscriber_Number
        APP_Activation_Date5 = CON_Start_Date
        APP_Activation_Days5 = Matched_Distance
        if APP_Activation_Days5 == 0:
            APP_Activation_Weeks5 = 0
        if APP_Activation_Days5 <= -1:
            APP_Activation_Weeks5 = int((APP_Activation_Days5 + 1) / 7) - 1
        if APP_Activation_Days5 >= 1:
            APP_Activation_Weeks5 = int((APP_Activation_Days5 - 1) / 7) + 1
        APP_Activation_Month5 = CON_Period

    return (APP_Subscriptions, APP_Account_Number1, APP_Account_Number2, APP_Account_Number3, APP_Accounts,
            APP_Subscriber_Number1, APP_Subscriber_Number2, APP_Subscriber_Number3, APP_Subscriber_Number4, APP_Subscriber_Number5,
            APP_Activation_Date1, APP_Activation_Date2, APP_Activation_Date3, APP_Activation_Date4, APP_Activation_Date5,
            APP_Activation_Weeks1, APP_Activation_Weeks2, APP_Activation_Weeks3, APP_Activation_Weeks4, APP_Activation_Weeks5,
            APP_Activation_Month1, APP_Activation_Month2, APP_Activation_Month3, APP_Activation_Month4, APP_Activation_Month5)


schema_Applications_Contracts_Update = t.StructType([
    t.StructField("APP_Subscriptions", t.IntegerType(), True),
    t.StructField("APP_Account_Number1", t.LongType(), True),
    t.StructField("APP_Account_Number2", t.LongType(), True),
    t.StructField("APP_Account_Number3", t.LongType(), True),
    t.StructField("APP_Accounts", t.StringType(), True),
    t.StructField("APP_Subscriber_Number1", t.LongType(), True),
    t.StructField("APP_Subscriber_Number2", t.LongType(), True),
    t.StructField("APP_Subscriber_Number3", t.LongType(), True),
    t.StructField("APP_Subscriber_Number4", t.LongType(), True),
    t.StructField("APP_Subscriber_Number5", t.LongType(), True),
    t.StructField("APP_Activation_Date1", t.DateType(), True),
    t.StructField("APP_Activation_Date2", t.DateType(), True),
    t.StructField("APP_Activation_Date3", t.DateType(), True),
    t.StructField("APP_Activation_Date4", t.DateType(), True),
    t.StructField("APP_Activation_Date5", t.DateType(), True),
    t.StructField("APP_Activation_Weeks1", t.IntegerType(), True),
    t.StructField("APP_Activation_Weeks2", t.IntegerType(), True),
    t.StructField("APP_Activation_Weeks3", t.IntegerType(), True),
    t.StructField("APP_Activation_Weeks4", t.IntegerType(), True),
    t.StructField("APP_Activation_Weeks5", t.IntegerType(), True),
    t.StructField("APP_Activation_Month1", t.IntegerType(), True),
    t.StructField("APP_Activation_Month2", t.IntegerType(), True),
    t.StructField("APP_Activation_Month3", t.IntegerType(), True),
    t.StructField("APP_Activation_Month4", t.IntegerType(), True),
    t.StructField("APP_Activation_Month5", t.IntegerType(), True)
])

udf_Applications_Contracts_Update = f.udf(Applications_Contracts_Update,
                                          returnType=schema_Applications_Contracts_Update)


def Match_Applications_Contracts(sdf_0):
    sdf_0a = sdf_0\
        .repartition(1)\
        .orderBy([f.col("APP_Record_Number").asc()])

    windowspec = Window\
        .partitionBy(f.col("APP_Record_Number"))\
        .orderBy([f.col("APP_Record_Number").asc()])

    sdf_0b = sdf_0a\
        .repartition(1)\
        .withColumn("RET_Record_Number", f.lag(f.col("APP_Record_Number"), 1).over(windowspec))

    sdf_1 = sdf_0b\
        .filter(f.col("APP_Date").isNotNull())

    # Calculated the distance between an application and a matched activation.
    sdf_2 = sdf_1\
        .withColumn("Matched_Distance", f.datediff(f.col("CON_Start_Date"), f.col("APP_Date")))

    # Based on the distance and application status sequence, matches and update the associated filters.
    sdf_3 = sdf_2\
        .withColumn("nest",
                    udf_Filter_Activation_Status(f.col("Matched_Distance"),
                                                 f.col("Filter_Decision_Outcome_Declined"),
                                                 f.col("Filter_Decision_Outcome_Arrears"),
                                                 f.col("Filter_Decision_Outcome_Referred"),
                                                 f.col("Filter_Decision_Outcome_Approved"),
                                                 f.col("Filter_Declined_No_Activations"),
                                                 f.col("Filter_Arrears_No_Activations"),
                                                 f.col("Filter_Referred_No_Activations"),
                                                 f.col("Filter_Approved_No_Activations"),
                                                 f.col("Filter_Declined_With_Activations"),
                                                 f.col("Filter_Arrears_With_Activations"),
                                                 f.col("Filter_Referred_With_Activations"),
                                                 f.col("Filter_Approved_With_Activations")))
    sdf_4 = sdf_3\
        .withColumn("FILTER_ACTIVATION_SEQ", f.col("nest.FILTER_ACTIVATION_SEQ"))\
        .withColumn("FILTER_DECLINED_NO_ACTIVATIONS", f.col("nest.FILTER_DECLINED_NO_ACTIVATIONS"))\
        .withColumn("FILTER_ARREARS_NO_ACTIVATIONS", f.col("nest.FILTER_ARREARS_NO_ACTIVATIONS"))\
        .withColumn("FILTER_REFERRED_NO_ACTIVATIONS", f.col("nest.FILTER_REFERRED_NO_ACTIVATIONS"))\
        .withColumn("FILTER_APPROVED_NO_ACTIVATIONS", f.col("nest.FILTER_APPROVED_NO_ACTIVATIONS"))\
        .withColumn("FILTER_DECLINED_WITH_ACTIVATIONS", f.col("nest.FILTER_DECLINED_WITH_ACTIVATIONS"))\
        .withColumn("FILTER_ARREARS_WITH_ACTIVATIONS", f.col("nest.FILTER_ARREARS_WITH_ACTIVATIONS"))\
        .withColumn("FILTER_REFERRED_WITH_ACTIVATIONS", f.col("nest.FILTER_REFERRED_WITH_ACTIVATIONS"))\
        .withColumn("FILTER_APPROVED_WITH_ACTIVATIONS", f.col("nest.FILTER_APPROVED_WITH_ACTIVATIONS"))\
        .drop(*["nest"])

    sdf_5 = sdf_4\
        .withColumn("nest",
                    f.when(f.col("Matched_Distance").isNotNull() &
                           (f.col("APP_Record_Number") != f.col("RET_Record_Number")),
                           udf_Applications_Contracts_Update(f.lit(1),
                                                             f.col("Account"),
                                                             f.col("APP_Account_Number1"),
                                                             f.col("APP_Account_Number2"),
                                                             f.col("APP_Account_Number3"),
                                                             f.col("Subscriber_Number"),
                                                             f.col("CON_Start_Date"),
                                                             f.col("Matched_Distance"),
                                                             f.col("CON_Period")))
                     .when(f.col("Matched_Distance").isNotNull() &
                           (f.col("APP_Record_Number") == f.col("RET_Record_Number")) &
                           (f.col("APP_Subscriptions") == 1),
                           udf_Applications_Contracts_Update(f.lit(2),
                                                             f.col("Account"),
                                                             f.col("APP_Account_Number1"),
                                                             f.col("APP_Account_Number2"),
                                                             f.col("APP_Account_Number3"),
                                                             f.col("Subscriber_Number"),
                                                             f.col("CON_Start_Date"),
                                                             f.col("Matched_Distance"),
                                                             f.col("CON_Period")))
                    .when(f.col("Matched_Distance").isNotNull() &
                          (f.col("APP_Record_Number") == f.col("RET_Record_Number")) &
                          (f.col("APP_Subscriptions") == 2),
                          udf_Applications_Contracts_Update(f.lit(3),
                                                            f.col("Account"),
                                                            f.col("APP_Account_Number1"),
                                                            f.col("APP_Account_Number2"),
                                                            f.col("APP_Account_Number3"),
                                                            f.col("Subscriber_Number"),
                                                            f.col("CON_Start_Date"),
                                                            f.col("Matched_Distance"),
                                                            f.col("CON_Period")))
                    .when(f.col("Matched_Distance").isNotNull() &
                          (f.col("APP_Record_Number") == f.col("RET_Record_Number")) &
                          (f.col("APP_Subscriptions") == 3),
                          udf_Applications_Contracts_Update(f.lit(4),
                                                            f.col("Account"),
                                                            f.col("APP_Account_Number1"),
                                                            f.col("APP_Account_Number2"),
                                                            f.col("APP_Account_Number3"),
                                                            f.col("Subscriber_Number"),
                                                            f.col("CON_Start_Date"),
                                                            f.col("Matched_Distance"),
                                                            f.col("CON_Period")))
                    .when(f.col("Matched_Distance").isNotNull() &
                          (f.col("APP_Record_Number") == f.col("RET_Record_Number")) &
                          (f.col("APP_Subscriptions") == 4),
                          udf_Applications_Contracts_Update(f.lit(5),
                                                            f.col("Account"),
                                                            f.col("APP_Account_Number1"),
                                                            f.col("APP_Account_Number2"),
                                                            f.col("APP_Account_Number3"),
                                                            f.col("Subscriber_Number"),
                                                            f.col("CON_Start_Date"),
                                                            f.col("Matched_Distance"),
                                                            f.col("CON_Period")))
                    .otherwise([None for _ in range(25)]))

    sdf_6 = sdf_5\
        .withColumn("APP_Subscriptions", f.col("nest.APP_Subscriptions"))\
        .withColumn("APP_Account_Number1", f.col("nest.APP_Account_Number1"))\
        .withColumn("APP_Account_Number2", f.col("nest.APP_Account_Number2"))\
        .withColumn("APP_Account_Number3", f.col("nest.APP_Account_Number3"))\
        .withColumn("APP_Accounts", f.col("nest.APP_Accounts"))\
        .withColumn("APP_Subscriber_Number1", f.col("nest.APP_Subscriber_Number1"))\
        .withColumn("APP_Subscriber_Number2", f.col("nest.APP_Subscriber_Number2"))\
        .withColumn("APP_Subscriber_Number3", f.col("nest.APP_Subscriber_Number3"))\
        .withColumn("APP_Subscriber_Number4", f.col("nest.APP_Subscriber_Number4"))\
        .withColumn("APP_Subscriber_Number5", f.col("nest.APP_Subscriber_Number5"))\
        .withColumn("APP_Activation_Date1", f.col("nest.APP_Activation_Date1"))\
        .withColumn("APP_Activation_Date2", f.col("nest.APP_Activation_Date2"))\
        .withColumn("APP_Activation_Date3", f.col("nest.APP_Activation_Date3"))\
        .withColumn("APP_Activation_Date4", f.col("nest.APP_Activation_Date4"))\
        .withColumn("APP_Activation_Date5", f.col("nest.APP_Activation_Date5"))\
        .withColumn("APP_Activation_Weeks1", f.col("nest.APP_Activation_Weeks1"))\
        .withColumn("APP_Activation_Weeks2", f.col("nest.APP_Activation_Weeks2"))\
        .withColumn("APP_Activation_Weeks3", f.col("nest.APP_Activation_Weeks3"))\
        .withColumn("APP_Activation_Weeks4", f.col("nest.APP_Activation_Weeks4"))\
        .withColumn("APP_Activation_Weeks5", f.col("nest.APP_Activation_Weeks5"))\
        .withColumn("APP_Activation_Month1", f.col("nest.APP_Activation_Month1"))\
        .withColumn("APP_Activation_Month2", f.col("nest.APP_Activation_Month2"))\
        .withColumn("APP_Activation_Month3", f.col("nest.APP_Activation_Month3"))\
        .withColumn("APP_Activation_Month4", f.col("nest.APP_Activation_Month4"))\
        .withColumn("APP_Activation_Month5", f.col("nest.APP_Activation_Month5"))\
        .drop(*["nest"])

    ls_keep = [
        "AIL_AvgMonthsOnBook",
        "ALL_AvgMonthsOnBook",
        "ALL_DaysSinceMRPayment",
        "ALL_MaxDelq180DaysLT24M",
        "ALL_MaxDelqEver",
        "ALL_Notices5Years",
        "ALL_Num0Delq1Year",
        "ALL_NumEnqs180Days",
        "ALL_NumEnqs30Days",
        "ALL_NumEnqs7Days",
        "ALL_NumEnqs90Days",
        "ALL_NumPayments2Years",
        "ALL_NumPayments90Days",
        "ALL_NumTrades180Days",
        "ALL_NumTrades30Days",
        "ALL_NumTrades90Days",
        "ALL_Perc0Delq90Days",
        "ALL_PercPayments2Years",
        "ALL_PercPayments90Days",
        "ALL_TimeOldestTrade",
        "ALT_AirtimePurchasedAvg36M",
        "ALT_TAU",
        "APP_Account_Number1",
        "APP_Account_Number2",
        "APP_Account_Number3",
        "APP_Account1",
        "APP_Account2",
        "APP_Account3",
        "APP_Account4",
        "APP_Account5",
        "APP_Accounts",
        "APP_Activation_Date1",
        "APP_Activation_Date2",
        "APP_Activation_Date3",
        "APP_Activation_Date4",
        "APP_Activation_Date5",
        "APP_Activation_Days1",
        "APP_Activation_Days2",
        "APP_Activation_Days3",
        "APP_Activation_Days4",
        "APP_Activation_Days5",
        "APP_Activation_Month1",
        "APP_Activation_Month2",
        "APP_Activation_Month3",
        "APP_Activation_Month4",
        "APP_Activation_Month5",
        "APP_Activation_Weeks1",
        "APP_Activation_Weeks2",
        "APP_Activation_Weeks3",
        "APP_Activation_Weeks4",
        "APP_Activation_Weeks5",
        "APP_Channel",
        "APP_Channel_CEC",
        "APP_Customer_Score",
        "APP_Customer_Score_CNT",
        "APP_Date",
        "APP_Decision_Outcome",
        "APP_Decision_Service",
        "APP_Decision_Service_Waterfall",
        "APP_Gross_Income",
        "APP_Gross_Income_CNT",
        "APP_IDNumber",
        "APP_Max_Product_Term",
        "APP_Max_Product_Term_CNT",
        "APP_Month",
        "APP_Predicted_Income",
        "APP_Predicted_Income_CNT",
        "APP_Record_Number",
        "APP_Risk_Grade",
        "APP_SLIR",
        "APP_Subscriber_Number1",
        "APP_Subscriber_Number2",
        "APP_Subscriber_Number3",
        "APP_Subscriber_Number4",
        "APP_Subscriber_Number5",
        "APP_Subscription_Limit",
        "APP_Subscription_Limit_CNT",
        "APP_Subscriptions",
        "BNK_NumOpenTrades",
        "CAM_Customer_Score",
        "CAM_Customer_Score_CNT",
        "CAM_Risk_Grade",
        "CBX_Prism_TM",
        "CBX_Prism_TM_CNT",
        "CBX_Sabre_TM",
        "CBX_Sabre_TM_CNT",
        "COM_NumOpenTrades",
        "COM_NumTrades2Years",
        "CRC_NumOpenTrades",
        "CSN_NumTrades60Days",
        "CST_Citizen",
        "CST_CustomerAge",
        "CST_DebtReviewGranted",
        "CST_DebtReviewRequested",
        "CST_Deceased",
        "CST_Dispute",
        "CST_Emigrated",
        "CST_Fraud",
        "CST_Sequestration",
        "DUP_Applicant",
        "DUP_Application_Sequence",
        "DUP_Calendar_Months_Skipped",
        "DUP_Days_Between_Applications",
        "DUP_Decision_Outcome",
        "DUP_Risk_Grade",
        "EST_Customer_Score",
        "EST_Customer_Score_CNT",
        "EST_Risk_Grade",
        "Filter_Approved_No_Activations",
        "Filter_Approved_With_Activations",
        "Filter_Arrears_Activations",
        "Filter_Arrears_No_Activations",
        "Filter_Arrears_State",
        "Filter_Arrears_With_Activations",
        "Filter_Channel_Dealer",
        "Filter_Channel_Franchise",
        "Filter_Channel_Inbound",
        "Filter_Channel_Online",
        "Filter_Channel_Other",
        "Filter_Channel_Outbound",
        "Filter_Channel_Store",
        "Filter_Clear_Activations",
        "Filter_Clear_State",
        "Filter_Decision_Outcome_Approved",
        "Filter_Decision_Outcome_Arrears",
        "Filter_Decision_Outcome_Declined",
        "Filter_Decision_Outcome_Referred",
        "Filter_Decision_Outcome_SEQ",
        "Filter_Decision_Outcome_Unknown",
        "Filter_Declined_No_Activations",
        "Filter_Declined_With_Activations",
        "Filter_DMP_Campaign",
        "Filter_DMP_Established",
        "Filter_DMP_New",
        "Filter_DMP_Unknown",
        "Filter_Erratic_Activations",
        "Filter_Erratic_State",
        "Filter_First_Account_Applicant",
        "Filter_Immature_Activations",
        "Filter_Immature_State",
        "Filter_New_To_Credit",
        "Filter_Other_Activations",
        "Filter_Referred_No_Activations",
        "Filter_Referred_With_Activations",
        "Filter_Responsible_Activations",
        "Filter_Responsible_State",
        "Filter_Risk_Grade_1",
        "Filter_Risk_Grade_2",
        "Filter_Risk_Grade_3",
        "Filter_Risk_Grade_4",
        "Filter_Risk_Grade_5",
        "Filter_Risk_Grade_6",
        "Filter_Risk_Grade_7",
        "Filter_Risk_Grade_8",
        "Filter_Risk_Grade_9",
        "Filter_Risk_Grade_X",
        "Filter_Telesales_Inbound",
        "Filter_Telesales_Outbound",
        "Filter_Web_Service",
        "Filter_XXXXXX_State",
        "FRN_NumOpenTrades",
        "GMP_Risk_Grade",
        "IDKey",
        "IDNumber",
        "NEW_Customer_Score",
        "NEW_Customer_Score_CNT",
        "NEW_Risk_Grade",
        "NTC_Accept_Final_Score_V01",
        "NTC_Accept_Final_Score_V01_CNT",
        "NTC_Accept_Risk_Score_V01",
        "NTC_Accept_Risk_Score_V01_CNT",
        "RCG_NumTradesUtilisedLT10",
        "UND_GMIP_Ratio",
        "UND_Risk_Grade",
        "UNN_PercTradesUtilisedLT100MR60",
        "UNS_MaxDelq1YearLT24M"
    ]

    sdf_7 = sdf_6\
        .select(*[ls_keep])

    return sdf_7