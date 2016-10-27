from setuptools import setup


def readme():
    with open('README.rst') as f:
        return f.read()


setup(name='pytwitterbot',
      version='0.1',
      description='Customizable twitter bot',
      url='http://github.com/n1amr/pytwitterbot',
      author='Amr Alaa',
      author_email='n1amr1@gmail.com',
      license='MIT',
      packages=['pytwitterbot'],
      install_requires=[
          'tweepy'],
      entry_points={
          'console_scripts': [
              'pytbot = pytwitterbot.__main__:entry_point']},
      zip_safe=False)
