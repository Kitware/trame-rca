# CHANGELOG


## v2.1.3 (2025-06-13)

### Bug Fixes

- **VtkWindow**: Fix performances during image flip
  ([`3284978`](https://github.com/Kitware/trame-rca/commit/328497890cb8651d8cdb5114faa7d87f17b5b92e))

- Remove array allocation during image flip


## v2.1.2 (2025-04-24)

### Bug Fixes

- **widget**: Add alias with warning to avoid breaking change
  ([`7dd242e`](https://github.com/Kitware/trame-rca/commit/7dd242e061c838a679005a931ecad48897d2b45d))


## v2.1.1 (2025-04-23)

### Bug Fixes

- **VtkWindow**: Fix flip and color inversion
  ([`3597106`](https://github.com/Kitware/trame-rca/commit/3597106b16e2cb5a3d700e70a8ed2b6eb6faecf1))

* Fix VtkWindow np image reshape which would produce flipped and blue rendering


## v2.1.0 (2025-04-16)

### Bug Fixes

- **tests**: Adapt test to match the refacto
  ([`e57fb87`](https://github.com/Kitware/trame-rca/commit/e57fb87bdd1e34684d9867f652c13c9d0e9d6772))

### Documentation

- Document abstract class
  ([`b078ff9`](https://github.com/Kitware/trame-rca/commit/b078ff9e40ef97b1decb7c307383956e461aad71))

### Features

- **vanilla-example**: Add vanilla example without vtk
  ([`ce9af29`](https://github.com/Kitware/trame-rca/commit/ce9af29da80b03148fee41d37a17c72c3a66b2bc))


## v2.0.2 (2025-04-02)

### Bug Fixes

- **ci**: Fix missing dependency
  ([`5122a27`](https://github.com/Kitware/trame-rca/commit/5122a2782cb2d9988b6bd9224d45c14d1480265d))

The `packaging` module was added in commit 263aad6c241d436dc2ec10a1ceb14a108d099a3c but it was
  missing from the requirements of this package.


## v2.0.1 (2025-03-27)

### Bug Fixes

- **rca_encoder**: Fix turbo JPEG encode color
  ([`fd6e3d6`](https://github.com/Kitware/trame-rca/commit/fd6e3d6ea5c31f6738c48ca222f1c31f3939aba4))


## v2.0.0 (2025-03-27)

### Bug Fixes

- Turbo-jpeg fallback
  ([`6b10a3b`](https://github.com/Kitware/trame-rca/commit/6b10a3b6668aa95170750f0eb0239ceec5240c07))

- **api**: Add update method and fix tests
  ([`7d4cb86`](https://github.com/Kitware/trame-rca/commit/7d4cb8657492def0c1b7a4f309fd020bbefa64e9))

### Features

- **api**: Big cleanup
  ([`b0b509d`](https://github.com/Kitware/trame-rca/commit/b0b509d973a99ee681f431f53cbb0434d89a7af1))


## v1.3.1 (2025-03-26)

### Bug Fixes

- **readme**: For pypi publish
  ([`ad71a1c`](https://github.com/Kitware/trame-rca/commit/ad71a1c95ab3ce933900731f19eaf5f928c92252))


## v1.3.0 (2025-03-26)

### Continuous Integration

- Install turbo-jpeg for tests
  ([`1fd21f9`](https://github.com/Kitware/trame-rca/commit/1fd21f988893a9b263c55ac2f3ed0624e7f0e78b))

### Features

- **encoder**: Add new turbo jpeg encoder
  ([`67c23a7`](https://github.com/Kitware/trame-rca/commit/67c23a76eb005c5a25e7712c1c28e15afce1fc89))

### Testing

- Fix api call
  ([`216ed29`](https://github.com/Kitware/trame-rca/commit/216ed293590422c43ae63cfad5369c03ba598aeb))


## v1.2.0 (2025-03-06)

### Bug Fixes

- **ci**: Fix missing dependency
  ([`fd0eece`](https://github.com/Kitware/trame-rca/commit/fd0eececd899f7ebea89f722d3154365e8900627))

* Add missing RcaViewAdapter dependencies

- **RcaRenderScheduler**: Fix RcaRenderScheduler meta type
  ([`dd1960f`](https://github.com/Kitware/trame-rca/commit/dd1960f24bb111ce5533cd710ae57ba4482c49b3))

* Fix RcaRenderScheduler wrong image meta type for Python 3.11+ caused by str Enum mixin behavior
  change.

### Features

- **RcaViewAdapter**: Add method to schedule render
  ([`c90edda`](https://github.com/Kitware/trame-rca/commit/c90eddacdd9ca44c1a9bc7413580d3fde6031fa2))

* Add method to schedule render from adapter * Update example with schedule render usage


## v1.1.1 (2025-02-07)

### Bug Fixes

- **RcaViewAdapter**: Enforce WindowResizeEvent on linux
  ([`263aad6`](https://github.com/Kitware/trame-rca/commit/263aad6c241d436dc2ec10a1ceb14a108d099a3c))

Manual invoke event can be removed when VTK has the following MR merged See
  https://gitlab.kitware.com/vtk/vtk/-/merge_requests/11905


## v1.1.0 (2025-01-20)

### Bug Fixes

- **ci**: Use pyproject and ruff
  ([`a4713c5`](https://github.com/Kitware/trame-rca/commit/a4713c53fa007331eb74922ae30b9934f11cec44))


## v0.7.0 (2025-01-20)

### Documentation

- Update README.rst
  ([`7334dde`](https://github.com/Kitware/trame-rca/commit/7334ddecd5890f48cac19e96b6f4265e9185cda1))

### Features

- **RcaViewAdapter**: Add helper classes to manage RCA views
  ([`56016fe`](https://github.com/Kitware/trame-rca/commit/56016fe9e71d3772e372f87e6374d055339598c6))

* Add RCA encoding with JPEG, WEBP, PNG, AVIF supported formats based on Pillow * Add
  RcaRenderScheduler and RcaViewAdapter to widget helper file * Update example to use helpers


## v0.6.0 (2024-11-07)

### Features

- **ImageDisplayArea**: Add support for conventional image types
  ([`fd00fa3`](https://github.com/Kitware/trame-rca/commit/fd00fa3039b6777bb33cb19ffde10bc3e843f4c4))


## v0.5.0 (2024-10-07)

### Features

- **RemoteControlledArea**: Add send mouse move property
  ([`ba9ad39`](https://github.com/Kitware/trame-rca/commit/ba9ad390aa37b67ed05f44210da219aacbb82935))

Add and forward send mouse move property to the RCA interactor style


## v0.4.4 (2024-06-16)

### Bug Fixes

- **StatisticsDisplay**: Fix data/sec counter
  ([`db080c3`](https://github.com/Kitware/trame-rca/commit/db080c344646d4edda6193590ca63bb1d19fe564))

content is now of Array type


## v0.4.3 (2024-06-05)

### Bug Fixes

- **decoder**: Use .buffer when sending arrays
  ([`824c7a8`](https://github.com/Kitware/trame-rca/commit/824c7a89b2ee6898ae2050696388b33b63ca7fd2))

fixes "DOMException: Failed to execute 'postMessage' on 'Worker': Value at index 0 does not have a
  transferable type"

- **MediaSourceDisplayArea**: Adapt for wslink>=2
  ([`de23267`](https://github.com/Kitware/trame-rca/commit/de232673ceff3f81d390012301c373c8425ce7d0))

This fixes the error " n.arrayBuffer is not a function" when using the MediaSourceDisplayArea

- **RawImageDisplayArea**: Use proper array type for rgba
  ([`12857b8`](https://github.com/Kitware/trame-rca/commit/12857b81e8b8963b64f2717272efa7ccabc73541))

Per ImageData documentation we need Uint8ClampedArray instead of just Uint8Array

- **VideoDecoder**: Flush before closing the decoder
  ([`4c484cf`](https://github.com/Kitware/trame-rca/commit/4c484cf1871d96d90ef3548b22d67c7d4a7a7343))

It seems to reduce the frequency of the 'Cannot call decode on closed codec' error

- **VideoDecoderDisplayArea**: Adapt for wslink>=2
  ([`9c4a990`](https://github.com/Kitware/trame-rca/commit/9c4a990285f2b136cd0e78d4c8544dcdfcf86fa1))

This fixes the error " n.arrayBuffer is not a function" when using the VideoDecoderDisplayArea.

- **vue**: Unmount components under both vue2 and vue3
  ([`f779ee5`](https://github.com/Kitware/trame-rca/commit/f779ee5652495ad5b52421ba08c02912494e0d14))

vue3 uses the callback beforeUnmount while vue2 beforeDestroy. This commit makes sure that the
  cleanup logic is called in both cases. A more clean solution would be to use the Composition API
  but I am not sure who to map all current patterns to the Composition API.


## v0.4.2 (2024-05-13)

### Bug Fixes

- **wslink**: Add support for wslink>2
  ([`813b6e2`](https://github.com/Kitware/trame-rca/commit/813b6e22be61c76070712ce76d72b7677f7b5021))

Co-authored-by: Sebastien Jourdain (Kitware) <sebastien.jourdain@kitware.com>


## v0.4.1 (2023-10-18)

### Bug Fixes

- **dependencies**: Update vtk-js
  ([`a694efe`](https://github.com/Kitware/trame-rca/commit/a694efe382e4eca6113be0095e44d4e9addb4818))

update version to 28.10.1 to include https://github.com/Kitware/vtk-js/pull/2911


## v0.4.0 (2023-09-29)

### Bug Fixes

- **pre-commit**: Handle black and flake8 conflict regarding W503
  ([`23eb6b2`](https://github.com/Kitware/trame-rca/commit/23eb6b2c81416306a7509c3c2f42921276cc11b3))

Black puts the operator after the newline while flake expects before. See also
  https://black.readthedocs.io/en/stable/guides/using_black_with_other_tools.html#flake8

### Continuous Integration

- Fix semantic-release version
  ([`6b06275`](https://github.com/Kitware/trame-rca/commit/6b06275f91b1f30c92b710276cbe94898cec911f))

### Features

- **events**: Forward start/end interaction events
  ([`6fd02a4`](https://github.com/Kitware/trame-rca/commit/6fd02a429ed2519c333b806381834dcfa4a5684d))

Allows to hook up start/stop Animation listeners on application side

- **events**: Use mousebutton as eventType
  ([`b79052a`](https://github.com/Kitware/trame-rca/commit/b79052adac5a4e059e51f25ab8447b0680644b25))

This brings the message structure closer to what VTK interactor expect

- **events**: Use vtk.js interactor
  ([`2819ab7`](https://github.com/Kitware/trame-rca/commit/2819ab72e0b7bd9fe8c12de2686bd179b5b52e36))

- **examples**: Add ViewAdapter example
  ([`80f6ba1`](https://github.com/Kitware/trame-rca/commit/80f6ba1b1b94fe506fc6f28c836c38d13ca9bfbf))

- **vue23**: Refactor code to be vue2/3 compatible
  ([`1d035a8`](https://github.com/Kitware/trame-rca/commit/1d035a8c16a6612632f3b41cd93346dba857f61f))


## v0.3.1 (2023-04-25)

### Bug Fixes

- **api**: Expose only meaningful classes
  ([`3ccff7c`](https://github.com/Kitware/trame-rca/commit/3ccff7c53680a29f1249372d5b3d2f146e9e1af5))


## v0.3.0 (2022-10-27)

### Features

- **RawImageDisplayArea**: Support rgb24 and rgba32 images
  ([`b77143a`](https://github.com/Kitware/trame-rca/commit/b77143a292e55148d060cae958053b1696fa1c08))


## v0.2.1 (2022-10-21)

### Bug Fixes

- **stats**: Allow stats to work on other pub/sub
  ([`b182e36`](https://github.com/Kitware/trame-rca/commit/b182e366cb5c2ffe718bced0d41e482f07c07b95))


## v0.2.0 (2022-10-16)

### Bug Fixes

- **VideoDecoder**: Code cleanup
  ([`32724b1`](https://github.com/Kitware/trame-rca/commit/32724b161262cbd6759c9293271afb7ef350bb07))

- **VideoDisplay**: Set source buffer in sequence mode
  ([`873ddc0`](https://github.com/Kitware/trame-rca/commit/873ddc0168a868f5a9f2c995c707f268df7a8f00))

### Features

- **VideoDisplayArea2**: Decode native vp9 bitstreams
  ([`43f4167`](https://github.com/Kitware/trame-rca/commit/43f41679c4c8ba6107ca4de6e568bd332cf5539d))


## v0.1.3 (2022-10-14)

### Bug Fixes

- **stats**: Improve stats
  ([`396a74f`](https://github.com/Kitware/trame-rca/commit/396a74fe5dae764a4e1e3b8c8e9e0f90d3289122))


## v0.1.2 (2022-10-13)

### Bug Fixes

- **FpsDisplay**: Add fps feedback
  ([`2ddea8d`](https://github.com/Kitware/trame-rca/commit/2ddea8dbca6da7f531a795c0e77a8470d9be4cd4))


## v0.1.1 (2022-10-13)

### Bug Fixes

- **VideoDisplayArea**: Parse initialization segment
  ([`6dd4960`](https://github.com/Kitware/trame-rca/commit/6dd4960bbe75b59c763f597e4fab551bdcdc3661))


## v0.1.0 (2022-10-13)

### Chores

- **version**: Revert to 0.0.0
  ([`839f34a`](https://github.com/Kitware/trame-rca/commit/839f34a045c520c85e8af0c0c137616719ea022e))

### Continuous Integration

- Reset version at 1.0.0
  ([`bc179de`](https://github.com/Kitware/trame-rca/commit/bc179de5b15df4fd836d4394dfdafb8aee2cdcca))

### Features

- **VideoDisplayArea**: Add video based DisplayArea
  ([`71d6e46`](https://github.com/Kitware/trame-rca/commit/71d6e46e2663d086e8ef2a011ac71a948144ee67))


## v1.0.0 (2022-10-11)

### Bug Fixes

- **rca-widget**: Start handling mouse interaction
  ([`dd42f82`](https://github.com/Kitware/trame-rca/commit/dd42f82ebb3e796397b55246c8fed0f62fa366a7))

- **vue**: Size handling done at RCA rather than display
  ([`b47a944`](https://github.com/Kitware/trame-rca/commit/b47a94472d09a875f9e9c4d8b38f60c47138f538))

### Chores

- Initial layout from cookie-cutter template
  ([`d34a69b`](https://github.com/Kitware/trame-rca/commit/d34a69b80d69fc8d91d4586be4f27ff71721cd35))

- **components**: Start building core components
  ([`58eb686`](https://github.com/Kitware/trame-rca/commit/58eb6868623fe9caed8ae194440a961749c0dcb5))
