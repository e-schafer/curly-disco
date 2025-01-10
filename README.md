#curly-disco

##login on github registry with docker

### Create a personal access token

-   In the upper-right corner of any page on GitHub, click your profile photo, then click Settings.
-   In the left sidebar, click Developer settings.
-   In the left sidebar, under Personal access tokens, click Tokens (classic).
-   Select Generate new token, then click Generate new token (classic).

### Log in to the GitHub Container Registry

```shell
export CR_PAT=ghp_...
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```
