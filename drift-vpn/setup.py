from setuptools import setup, find_packages


setup(
    name="drift-vpn",
    version='0.1.0',
    license='MIT',
    author="Directive Games North",
    author_email="info@directivegames.com",
    description="VPN Server for Drift Tiers.",
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    include_package_data=True,

    classifiers=[
        'Drift :: Tag :: Core',
        'Drift :: Tag :: VPNServer',
        'Environment :: Web Environment',
        'Framework :: Drift',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
