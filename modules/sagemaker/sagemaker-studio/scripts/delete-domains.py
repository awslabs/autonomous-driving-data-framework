import argparse
import time

import boto3
from botocore.config import Config

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        required=True,
        help="AWS region for which the domains should be deleted",
    )
    parser.add_argument(
        "-p",
        "--profile",
        type=str,
        required=True,
        help="AWS profile to use for authentication",
    )
    args = parser.parse_args()
    region = args.region
    aws_profile = args.profile

    conf = Config(
        region_name=region,
    )

    accept_input = f"delete-{region}"
    print(f"Are you certain you want to delete Sagemaker domain in: {region}. [{accept_input}]")
    print("This action cannot be undone")
    user_input = input()

    if user_input != accept_input:
        print(f"Cancelled. If you wish to delete the domain, please enter {accept_input}")
        exit(1)
    else:
        session = boto3.session.Session(profile_name=aws_profile)
        client = session.client("sagemaker", config=conf)

        def get_domains():
            req = client.list_domains()
            return req["Domains"]

        def get_apps(domainId):
            req = client.list_apps(DomainIdEquals=domainId)
            return req["Apps"]

        def get_user_profiles(domainId):
            req = client.list_user_profiles(
                DomainIdEquals=domainId,
            )
            return req["UserProfiles"]

        def delete_app(app):
            try:
                print(app["Status"])
                if app["Status"] != "Deleted":
                    client.delete_app(
                        DomainId=app["DomainId"],
                        UserProfileName=app["UserProfileName"],
                        AppType=app["AppType"],
                        AppName=app["AppName"],
                    )
                else:
                    print("App already delted")
            except Exception as e:
                print(f"\tError deleting app: {e}")

        def delete_user_profile(profile):
            try:
                client.delete_user_profile(
                    DomainId=profile["DomainId"],
                    UserProfileName=profile["UserProfileName"],
                )
            except Exception as e:
                print(f"\tError deleting user_profile: {e}")

        def delete_domain(domainId):
            try:
                client.delete_domain(DomainId=domainId, RetentionPolicy={"HomeEfsFileSystem": "Delete"})
            except Exception as e:
                print(f"\tError deleting domain: {e}")

        def wait_until_none(domainId, check):
            items = check(domainId)
            if items is not None and len(items) > 0:
                not_already_deleted = [x for x in items if x["Status"] != "Deleted"]
                if not_already_deleted is not None and len(not_already_deleted) > 0:
                    time.sleep(5)
                    wait_until_none(domainId, check)
                else:
                    print("found items, but they are already deleted")
            else:
                print("No items, found, moving on...")

        for domain in get_domains():
            domainId = domain["DomainId"]
            print(f"Getting apps for domain {domainId}")
            apps = get_apps(domainId)
            for app in apps:
                print(f"Deleting app: {app['AppName']}")
                # delete_app(app)
            # wait_until_none(domainId, get_apps)
            user_profiles = get_user_profiles(domainId)
            for profile in user_profiles:
                print(f"Deleting user profile: {profile['UserProfileName']}")
                # delete_user_profile(profile)
            # wait_until_none(domainId, get_user_profiles)
            # delete_domain(domainId)
            print(f"Done deleting domain {domainId}")
