from distutils.core import setup

setup(
    name='p4a-build',
    version='1.0.2',
    author='Mathieu Virbel',
    author_email='mat@kivy.org',
    scripts=['p4a-build'],
    description='Build tool for P4A Build Cloud',
    install_requires=['requests']
)
